from __future__ import annotations

import os
import re
import shutil
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import Book, Chapter
from .site import (
    IMAGE_HOSTS,
    USER_AGENT,
    AntiRobotRequired,
    ManhuaGuiClient,
    ManhuaGuiError,
)


ProgressCallback = Callable[[str, int, int, str], None]

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_filename(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = (cleaned or fallback)[:80]
    if cleaned.partition(".")[0].upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"[:80]
    return cleaned


def _page_extension(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix):
        return suffix
    return ".jpg"


def _host_candidates(url: str) -> list[str]:
    parsed = urlparse(url)
    current = parsed.hostname or ""
    candidates = [url]
    if current.endswith(".hamreus.com"):
        for host in IMAGE_HOSTS:
            replacement = f"{host}.hamreus.com"
            if replacement != current:
                candidates.append(url.replace(current, replacement, 1))
    return candidates


class _Progress:
    def __init__(self, chapter_title: str, total: int) -> None:
        self.chapter_title = chapter_title
        self.total = total
        self.completed = 0
        self.skipped = 0
        self._lock = threading.Lock()

    def advance(self, skipped: bool) -> None:
        with self._lock:
            self.completed += 1
            if skipped:
                self.skipped += 1
            suffix = f"，复用 {self.skipped}" if self.skipped else ""
            print(
                f"\r  {self.chapter_title}: {self.completed}/{self.total}{suffix}",
                end="",
                flush=True,
            )
            if self.completed == self.total:
                print()


class ChapterDownloader:
    def __init__(
        self,
        client: ManhuaGuiClient,
        output_dir: Path,
        workers: int = 4,
        retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self.client = client
        self.output_dir = output_dir
        self.workers = max(1, workers)
        self.retries = max(1, retries)
        self.timeout = timeout

    def download_book(self, book: Book, chapters: list[Chapter]) -> list[Path]:
        archives: list[Path] = []

        for position, chapter in enumerate(chapters, start=1):
            print(f"\n[{position}/{len(chapters)}] {chapter.title}")
            archive, skipped = self.download_chapter(book, chapter)
            if skipped:
                print(f"  已存在，跳过: {archive.name}")
            archives.append(archive)
            if not skipped:
                print(f"  已打包: {archive.name}")
        return archives

    def download_chapter(
        self,
        book: Book,
        chapter: Chapter,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[Path, bool]:
        book_dir = self.output_dir / safe_filename(book.title, book.book_id)
        work_root = book_dir / ".manhuagui-work"
        archive = archive_path_for(self.output_dir, book, chapter)
        book_dir.mkdir(parents=True, exist_ok=True)
        if archive.is_file() and archive.stat().st_size > 0:
            if progress_callback:
                progress_callback("completed", 1, 1, "ZIP 已存在")
            return archive, True

        if progress_callback:
            progress_callback("preparing", 0, 0, "正在读取图片列表")
        page_urls = self.client.fetch_chapter_images(chapter, book.url)
        chapter_work = work_root / chapter.chapter_id
        chapter_work.mkdir(parents=True, exist_ok=True)
        terminal_progress = (
            None if progress_callback else _Progress(chapter.title, len(page_urls))
        )
        if progress_callback:
            progress_callback(
                "downloading",
                0,
                len(page_urls),
                "正在下载图片",
            )

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = []
            width = max(3, len(str(len(page_urls))))
            for page_number, page_url in enumerate(page_urls, start=1):
                destination = chapter_work / (
                    f"{page_number:0{width}d}{_page_extension(page_url)}"
                )
                futures.append(
                    executor.submit(
                        self._download_page,
                        page_url,
                        destination,
                        chapter.url,
                    )
                )
            completed = 0
            try:
                for future in as_completed(futures):
                    skipped = future.result()
                    completed += 1
                    if terminal_progress:
                        terminal_progress.advance(skipped=skipped)
                    if progress_callback:
                        progress_callback(
                            "downloading",
                            completed,
                            len(page_urls),
                            "正在下载图片",
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise

        if progress_callback:
            progress_callback(
                "packing",
                len(page_urls),
                len(page_urls),
                "正在创建 ZIP",
            )
        self._make_zip(chapter_work, archive)
        shutil.rmtree(chapter_work)
        if work_root.exists() and not any(work_root.iterdir()):
            work_root.rmdir()
        if progress_callback:
            progress_callback(
                "completed",
                len(page_urls),
                len(page_urls),
                "下载完成",
            )
        return archive, False

    def _download_page(self, url: str, destination: Path, referer: str) -> bool:
        if destination.is_file() and destination.stat().st_size > 0:
            return True

        partial = destination.with_name(destination.name + ".part")
        last_error: BaseException | None = None
        candidates = _host_candidates(url)
        for attempt in range(self.retries):
            candidate = candidates[attempt % len(candidates)]
            try:
                self._download_once(candidate, partial, destination, referer)
                return False
            except HTTPError as exc:
                last_error = exc
                if exc.code == 416 and partial.exists():
                    partial.unlink()
                elif exc.code not in {403, 408, 429, 500, 502, 503, 504}:
                    break
            except (URLError, OSError, ManhuaGuiError) as exc:
                last_error = exc
            if attempt + 1 < self.retries:
                time.sleep(min(2**attempt, 4))
        if isinstance(last_error, HTTPError) and last_error.code in {403, 429, 503}:
            raise AntiRobotRequired(referer)
        raise ManhuaGuiError(f"图片下载失败: {url} ({last_error})")

    def _download_once(
        self,
        url: str,
        partial: Path,
        destination: Path,
        referer: str,
    ) -> None:
        existing = partial.stat().st_size if partial.exists() else 0
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/png,image/*;q=0.8,*/*;q=0.5",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer,
        }
        if existing:
            headers["Range"] = f"bytes={existing}-"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout) as response:
            status = getattr(response, "status", response.getcode())
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type.startswith("text/") or "html" in content_type:
                raise ManhuaGuiError(f"图片节点返回了 {content_type or '文本内容'}")
            append = existing > 0 and status == 206
            mode = "ab" if append else "wb"
            expected = response.headers.get("Content-Length")
            received = 0
            with partial.open(mode) as target:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
                    received += len(chunk)
                target.flush()
                os.fsync(target.fileno())
            if expected is not None and received != int(expected):
                raise ManhuaGuiError(
                    f"图片传输不完整: 预期 {expected} 字节，收到 {received} 字节"
                )
        if partial.stat().st_size == 0:
            raise ManhuaGuiError("图片内容为空")
        partial.replace(destination)

    @staticmethod
    def _make_zip(chapter_work: Path, archive: Path) -> None:
        temporary = archive.with_name(archive.name + ".part")
        if temporary.exists():
            temporary.unlink()
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as output:
                for image in sorted(chapter_work.iterdir()):
                    if image.is_file() and not image.name.endswith(".part"):
                        output.write(image, arcname=image.name)
            with zipfile.ZipFile(temporary, "r") as check:
                bad_file = check.testzip()
                if bad_file:
                    raise ManhuaGuiError(f"ZIP 校验失败: {bad_file}")
            temporary.replace(archive)
        except BaseException:
            if temporary.exists():
                temporary.unlink()
            raise


def archive_path_for(output_dir: Path, book: Book, chapter: Chapter) -> Path:
    book_dir = output_dir / safe_filename(book.title, book.book_id)
    return book_dir / (
        f"{chapter.index:03d}_{safe_filename(chapter.title, chapter.chapter_id)}.zip"
    )
