from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def host_target_triple() -> str:
    configured = os.environ.get("TAURI_ENV_TARGET_TRIPLE")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["rustc", "-vV"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "没有找到 Rust 工具链。安装 Rust 后重试，"
            "或使用 --target-triple 指定当前 Tauri 目标。"
        ) from exc
    for line in result.stdout.splitlines():
        if line.startswith("host: "):
            return line.removeprefix("host: ").strip()
    raise SystemExit("无法从 rustc -vV 读取目标三元组")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Python Tauri sidecar")
    parser.add_argument("--target-triple")
    args = parser.parse_args()
    target = args.target_triple or host_target_triple()

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "打包桌面应用需要 PyInstaller：python3 -m pip install pyinstaller"
        ) from exc

    build_root = ROOT / "build" / "sidecar"
    dist_dir = build_root / "dist"
    work_dir = build_root / "work"
    spec_dir = build_root / "spec"
    for directory in (dist_dir, work_dir, spec_dir):
        directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "manhuagui-backend",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(work_dir),
            "--specpath",
            str(spec_dir),
            "--paths",
            str(ROOT),
            str(ROOT / "scripts" / "backend_entry.py"),
        ],
        cwd=ROOT,
        check=True,
    )

    suffix = ".exe" if sys.platform == "win32" else ""
    source = dist_dir / f"manhuagui-backend{suffix}"
    destination_dir = ROOT / "src-tauri" / "binaries"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"manhuagui-backend-{target}{suffix}"
    shutil.copy2(source, destination)
    if sys.platform != "win32":
        destination.chmod(destination.stat().st_mode | 0o111)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
