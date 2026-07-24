use std::sync::Mutex;

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::{
    process::CommandChild,
    ShellExt,
};
use url::Url;

struct SidecarState(Mutex<Option<CommandChild>>);

fn checked_manhuagui_url(value: &str) -> Result<Url, String> {
    let url = Url::parse(value).map_err(|error| format!("验证地址无效: {error}"))?;
    if !matches!(url.scheme(), "http" | "https") {
        return Err("验证地址必须使用 HTTP 或 HTTPS".into());
    }
    let host = url.host_str().unwrap_or_default().to_ascii_lowercase();
    if host != "manhuagui.com" && !host.ends_with(".manhuagui.com") {
        return Err("只允许打开 manhuagui.com 的验证页面".into());
    }
    Ok(url)
}

#[tauri::command]
fn open_verification_window(app: AppHandle, url: String) -> Result<(), String> {
    let url = checked_manhuagui_url(&url)?;
    if let Some(window) = app.get_webview_window("verification") {
        window
            .navigate(url)
            .map_err(|error| format!("验证窗口无法跳转: {error}"))?;
        window
            .set_focus()
            .map_err(|error| format!("验证窗口无法显示: {error}"))?;
        return Ok(());
    }

    WebviewWindowBuilder::new(
        &app,
        "verification",
        WebviewUrl::External(url),
    )
    .title("完成 ManhuaGui 人机验证")
    .inner_size(980.0, 760.0)
    .min_inner_size(720.0, 560.0)
    .center()
    .build()
    .map_err(|error| format!("验证窗口无法打开: {error}"))?;
    Ok(())
}

#[tauri::command]
async fn read_verification_cookies(
    app: AppHandle,
    url: String,
) -> Result<String, String> {
    let url = checked_manhuagui_url(&url)?;
    let window = app
        .get_webview_window("verification")
        .ok_or_else(|| "验证窗口尚未打开".to_string())?;
    let cookies = window
        .cookies_for_url(url)
        .map_err(|error| format!("无法读取验证 Cookie: {error}"))?;
    let header = cookies
        .iter()
        .map(|cookie| format!("{}={}", cookie.name(), cookie.value()))
        .collect::<Vec<_>>()
        .join("; ");
    if header.is_empty() {
        return Err("验证窗口没有可用 Cookie，请确认页面已经通过验证".into());
    }
    Ok(header)
}

#[tauri::command]
fn close_verification_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("verification") {
        window
            .close()
            .map_err(|error| format!("验证窗口无法关闭: {error}"))?;
    }
    Ok(())
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<SidecarState>();
    if let Ok(mut guard) = state.0.lock() {
        if let Some(child) = guard.take() {
            let _ = child.kill();
        }
    };
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            open_verification_window,
            read_verification_cookies,
            close_verification_window
        ])
        .setup(|app| {
            let child = if cfg!(debug_assertions) {
                None
            } else {
                let parent_pid = std::process::id().to_string();
                let sidecar = app
                    .shell()
                    .sidecar("manhuagui-backend")
                    .map_err(|error| format!("无法准备本地下载服务: {error}"))?;
                let (mut events, child) = sidecar
                    .args([
                        "--port",
                        "48135",
                        "--parent-pid",
                        parent_pid.as_str(),
                    ])
                    .spawn()
                    .map_err(|error| format!("无法启动本地下载服务: {error}"))?;
                tauri::async_runtime::spawn(async move {
                    while events.recv().await.is_some() {}
                });
                Some(child)
            };
            app.manage(SidecarState(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Tauri application failed to build");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_sidecar(app_handle);
        }
    });
}
