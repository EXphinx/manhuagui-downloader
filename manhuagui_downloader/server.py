from __future__ import annotations

import argparse
import ctypes
import json
import mimetypes
import os
import signal
import threading
from ctypes import wintypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import __version__
from .site import AntiRobotRequired, ManhuaGuiClient, ManhuaGuiError
from .tasks import TaskManager


ALLOWED_ORIGINS = {
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
}
IS_WINDOWS = os.name == "nt"


class APIError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        manager: TaskManager,
        ui_dir: Path | None,
    ) -> None:
        self.manager = manager
        self.ui_dir = ui_dir.resolve() if ui_dir else None
        super().__init__(address, AppRequestHandler)

    def server_close(self) -> None:
        self.manager.close()
        super().server_close()


class AppRequestHandler(BaseHTTPRequestHandler):
    server: AppServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[api] {self.address_string()} {format % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/"):
                self._handle_api(method, path)
            elif method == "GET":
                self._serve_ui(path)
            else:
                raise APIError(404, "not_found", "接口不存在")
        except AntiRobotRequired as exc:
            self._json(
                409,
                {
                    "error": {
                        "code": "anti_robot",
                        "message": str(exc),
                        "verification_url": exc.url,
                    }
                },
            )
        except APIError as exc:
            self._json(
                exc.status,
                {"error": {"code": exc.code, "message": str(exc)}},
            )
        except ManhuaGuiError as exc:
            code = (
                "directory_required"
                if str(exc) == "请先选择下载目录"
                else "operation_failed"
            )
            self._json(
                409 if code == "directory_required" else 400,
                {"error": {"code": code, "message": str(exc)}},
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(
                400,
                {"error": {"code": "invalid_request", "message": str(exc)}},
            )
        except Exception as exc:
            self._json(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": f"后端处理失败: {exc}",
                    }
                },
            )

    def _handle_api(self, method: str, path: str) -> None:
        manager = self.server.manager
        if method == "GET" and path == "/api/health":
            self._json(
                200,
                {
                    "app": "manhuagui-downloader",
                    "version": __version__,
                    "status": "ok",
                },
            )
            return
        if method == "GET" and path == "/api/settings":
            self._json(200, manager.settings())
            return
        if method == "POST" and path == "/api/settings/directory":
            body = self._read_json()
            self._json(200, manager.set_directory(self._string(body, "path")))
            return
        if method == "POST" and path == "/api/books/inspect":
            body = self._read_json()
            self._json(200, manager.inspect_book(self._string(body, "url")))
            return
        if method == "GET" and path == "/api/tasks":
            self._json(200, {"tasks": manager.list_tasks()})
            return
        if method == "POST" and path == "/api/tasks":
            body = self._read_json()
            indexes = body.get("chapter_indexes")
            if not isinstance(indexes, list) or not all(
                isinstance(index, int) and not isinstance(index, bool)
                for index in indexes
            ):
                raise ValueError("chapter_indexes 必须是章节序号数组")
            result = manager.create_tasks(
                self._string(body, "inspection_id"),
                indexes,
            )
            self._json(201, result)
            return
        if method == "DELETE" and path.startswith("/api/tasks/"):
            task_id = unquote(path.removeprefix("/api/tasks/"))
            if not task_id or "/" in task_id:
                raise APIError(404, "not_found", "任务不存在")
            manager.delete_task(task_id)
            self._json(200, {"deleted": task_id})
            return
        if method == "POST" and path == "/api/anti-robot/cookies":
            body = self._read_json()
            count = manager.apply_verification_cookies(
                self._string(body, "cookie")
            )
            self._json(200, {"retried_tasks": count})
            return
        raise APIError(404, "not_found", "接口不存在")

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length 无效") from exc
        if length <= 0:
            return {}
        if length > 1_000_000:
            raise APIError(413, "payload_too_large", "请求内容过大")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("请求内容必须是 JSON 对象")
        return value

    @staticmethod
    def _string(body: dict[str, Any], key: str) -> str:
        value = body.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} 不能为空")
        return value.strip()

    def _serve_ui(self, request_path: str) -> None:
        ui_dir = self.server.ui_dir
        if ui_dir is None:
            raise APIError(404, "not_found", "网页前端尚未构建")
        relative = unquote(request_path).lstrip("/") or "index.html"
        candidate = (ui_dir / relative).resolve()
        if ui_dir not in candidate.parents and candidate != ui_dir:
            raise APIError(403, "forbidden", "路径不可访问")
        if not candidate.is_file():
            candidate = ui_dir / "index.html"
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(candidate.name)[0] or "application/octet-stream",
        )
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")


def _windows_process_exists(process_id: int) -> bool:
    process_query_limited_information = 0x1000
    still_active = 259
    error_access_denied = 5

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(
        process_query_limited_information,
        False,
        process_id,
    )
    if not handle:
        return ctypes.get_last_error() == error_access_denied
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


def _parent_exists(parent_pid: int) -> bool:
    if parent_pid <= 0:
        return True
    if IS_WINDOWS:
        return _windows_process_exists(parent_pid)
    try:
        os.kill(parent_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _watch_parent(server: AppServer, parent_pid: int) -> None:
    while _parent_exists(parent_pid):
        threading.Event().wait(1.0)
    server.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ManhuaGui Downloader local API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=48135, type=int)
    parser.add_argument("--ui", type=Path)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("后端只允许监听本机回环地址")
    manager = TaskManager(ManhuaGuiClient(), workers=max(1, args.workers))
    server = AppServer((args.host, args.port), manager, args.ui)

    if args.parent_pid:
        threading.Thread(
            target=_watch_parent,
            args=(server, args.parent_pid),
            name="manhuagui-parent-watch",
            daemon=True,
        ).start()

    def stop_server(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)
    print(f"ManhuaGui API: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
