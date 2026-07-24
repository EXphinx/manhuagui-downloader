const DOWNLOAD_DIRECTORY_KEY = "manhuagui.download-directory";

export function savedDirectory(): string | null {
  return window.localStorage.getItem(DOWNLOAD_DIRECTORY_KEY);
}

export function rememberDirectory(path: string): void {
  window.localStorage.setItem(DOWNLOAD_DIRECTORY_KEY, path);
}

export function isDesktopApp(): boolean {
  return Boolean(window.__TAURI_INTERNALS__);
}

export async function chooseDirectory(
  defaultPath?: string | null,
): Promise<string | null> {
  if (isDesktopApp()) {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const result = await open({
      directory: true,
      multiple: false,
      canCreateDirectories: true,
      defaultPath: defaultPath ?? undefined,
      title: "选择漫画下载目录",
    });
    return typeof result === "string" ? result : null;
  }
  const result = window.prompt(
    "浏览器开发模式无法打开系统目录选择器，请输入完整下载路径：",
    defaultPath ?? "",
  );
  return result?.trim() || null;
}

export async function openVerificationWindow(url: string): Promise<void> {
  if (isDesktopApp()) {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("open_verification_window", { url });
    return;
  }
  const opened = window.open(url, "_blank", "noopener,noreferrer");
  if (!opened) {
    throw new Error("浏览器阻止了验证窗口，请允许此页面打开新窗口");
  }
}

export async function readVerificationCookies(
  url: string,
): Promise<string | null> {
  if (!isDesktopApp()) return null;
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<string>("read_verification_cookies", { url });
}

export async function closeVerificationWindow(): Promise<void> {
  if (!isDesktopApp()) return;
  const { invoke } = await import("@tauri-apps/api/core");
  await invoke("close_verification_window");
}
