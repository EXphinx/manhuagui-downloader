from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .downloader import ChapterDownloader, archive_path_for
from .models import Book, Chapter
from .site import AntiRobotRequired, ManhuaGuiClient, ManhuaGuiError


ACTIVE_STATUSES = {"queued", "preparing", "downloading", "packing", "blocked"}
REMOVABLE_STATUSES = {"queued", "blocked", "failed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class QueueTask:
    id: str
    book_id: str
    book_title: str
    book_url: str
    chapter_id: str
    chapter_index: int
    chapter_title: str
    chapter_url: str
    status: str
    current: int
    total: int
    detail: str
    error: str | None
    verification_url: str | None
    archive_path: str | None
    created_at: str
    updated_at: str

    def as_json(self) -> dict[str, Any]:
        return asdict(self)

    def to_book_and_chapter(self) -> tuple[Book, Chapter]:
        chapter = Chapter(
            index=self.chapter_index,
            chapter_id=self.chapter_id,
            title=self.chapter_title,
            url=self.chapter_url,
        )
        book = Book(
            book_id=self.book_id,
            title=self.book_title,
            url=self.book_url,
            chapters=(chapter,),
        )
        return book, chapter


class TaskManager:
    def __init__(self, client: ManhuaGuiClient, workers: int = 4) -> None:
        self.client = client
        self.workers = workers
        self.output_dir: Path | None = None
        self._tasks: dict[str, QueueTask] = {}
        self._inspections: dict[str, Book] = {}
        self._lock = threading.RLock()
        self._client_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._running_id: str | None = None
        self._last_persist = 0.0
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="manhuagui-download-queue",
            daemon=True,
        )
        self._worker.start()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()

    def settings(self) -> dict[str, Any]:
        with self._lock:
            return {
                "download_directory": str(self.output_dir) if self.output_dir else None,
                "running": self._running_id is not None,
            }

    def set_directory(self, value: str) -> dict[str, Any]:
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise ManhuaGuiError("下载目录必须使用完整路径")
        with self._lock:
            if self._running_id is not None:
                raise ManhuaGuiError("当前章节下载完成后才能更换目录")
        try:
            path.mkdir(parents=True, exist_ok=True)
            state_dir = path / ".manhuagui"
            state_dir.mkdir(parents=True, exist_ok=True)
            test_file = state_dir / f".write-test-{uuid.uuid4().hex}"
            test_file.touch(exist_ok=False)
            test_file.unlink()
        except OSError as exc:
            raise ManhuaGuiError(f"无法写入下载目录: {exc}") from exc

        with self._lock:
            previous_directory = self.output_dir
            previous_tasks = self._tasks
            self.output_dir = path.resolve()
            try:
                self._load_locked()
            except Exception:
                self.output_dir = previous_directory
                self._tasks = previous_tasks
                raise
            self._wake.set()
            return self.settings()

    def inspect_book(self, url: str) -> dict[str, Any]:
        self._require_directory()
        with self._client_lock:
            book = self.client.fetch_book(url)
        inspection_id = uuid.uuid4().hex
        with self._lock:
            self._inspections[inspection_id] = book
            while len(self._inspections) > 10:
                self._inspections.pop(next(iter(self._inspections)))
            output_dir = self._require_directory()
            task_by_chapter = {
                task.chapter_id: task
                for task in self._tasks.values()
                if task.book_id == book.book_id
            }
            chapters = []
            for chapter in book.chapters:
                archive = archive_path_for(output_dir, book, chapter)
                downloaded = archive.is_file() and archive.stat().st_size > 0
                related = task_by_chapter.get(chapter.chapter_id)
                task_status = related.status if related else None
                if task_status == "completed" and not downloaded:
                    task_status = None
                chapters.append(
                    {
                        "index": chapter.index,
                        "chapter_id": chapter.chapter_id,
                        "title": chapter.title,
                        "url": chapter.url,
                        "downloaded": downloaded,
                        "task_status": task_status,
                    }
                )
        return {
            "inspection_id": inspection_id,
            "book": {
                "book_id": book.book_id,
                "title": book.title,
                "url": book.url,
                "chapters": chapters,
            },
        }

    def create_tasks(
        self,
        inspection_id: str,
        chapter_indexes: list[int],
    ) -> dict[str, Any]:
        output_dir = self._require_directory()
        with self._lock:
            book = self._inspections.get(inspection_id)
            if not book:
                raise ManhuaGuiError("章节列表已失效，请重新读取漫画链接")
            selected = set(chapter_indexes)
            chapters = [chapter for chapter in book.chapters if chapter.index in selected]
            if not chapters:
                raise ManhuaGuiError("请至少选择一个章节")
            if len(chapters) != len(selected):
                raise ManhuaGuiError("选择中包含不存在的章节序号")

            active_keys = {
                (task.book_id, task.chapter_id)
                for task in self._tasks.values()
                if task.status in ACTIVE_STATUSES
            }
            created: list[QueueTask] = []
            skipped = 0
            for chapter in chapters:
                key = (book.book_id, chapter.chapter_id)
                archive = archive_path_for(output_dir, book, chapter)
                if key in active_keys or (
                    archive.is_file() and archive.stat().st_size > 0
                ):
                    skipped += 1
                    continue
                timestamp = _now()
                task = QueueTask(
                    id=uuid.uuid4().hex,
                    book_id=book.book_id,
                    book_title=book.title,
                    book_url=book.url,
                    chapter_id=chapter.chapter_id,
                    chapter_index=chapter.index,
                    chapter_title=chapter.title,
                    chapter_url=chapter.url,
                    status="queued",
                    current=0,
                    total=0,
                    detail="等待下载",
                    error=None,
                    verification_url=None,
                    archive_path=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self._tasks[task.id] = task
                created.append(task)
                active_keys.add(key)
            self._persist_locked(force=True)
            self._wake.set()
            return {
                "created": [task.as_json() for task in created],
                "created_count": len(created),
                "skipped_count": skipped,
            }

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                task.as_json()
                for task in sorted(
                    self._tasks.values(),
                    key=lambda item: item.created_at,
                    reverse=True,
                )
            ]

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ManhuaGuiError("任务不存在或已经删除")
            if task.status not in REMOVABLE_STATUSES:
                raise ManhuaGuiError("只能取消等待中、验证中或失败的任务")
            del self._tasks[task_id]
            self._persist_locked(force=True)

    def apply_verification_cookies(self, cookie_header: str) -> int:
        if not cookie_header.strip():
            raise ManhuaGuiError("验证窗口没有可用 Cookie，请确认页面已经通过验证")
        self.client.set_cookie_header(cookie_header)
        count = 0
        with self._lock:
            for task in self._tasks.values():
                if task.status == "blocked":
                    task.status = "queued"
                    task.detail = "验证完成，等待重试"
                    task.error = None
                    task.verification_url = None
                    task.updated_at = _now()
                    count += 1
            self._persist_locked(force=True)
            self._wake.set()
        return count

    def _require_directory(self) -> Path:
        with self._lock:
            if self.output_dir is None:
                raise ManhuaGuiError("请先选择下载目录")
            return self.output_dir

    @property
    def _state_file(self) -> Path:
        output_dir = self._require_directory()
        return output_dir / ".manhuagui" / "tasks.json"

    def _load_locked(self) -> None:
        self._tasks = {}
        state_file = self._state_file
        if not state_file.exists():
            self._persist_locked(force=True)
            return
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            task_rows = payload.get("tasks", [])
            for row in task_rows:
                task = QueueTask(**row)
                if task.status in {"preparing", "downloading", "packing"}:
                    task.status = "queued"
                    task.detail = "应用重新启动，等待继续"
                    task.updated_at = _now()
                self._tasks[task.id] = task
        except (OSError, ValueError, TypeError) as exc:
            raise ManhuaGuiError(
                f"任务记录无法读取: {state_file} ({exc})"
            ) from exc
        self._persist_locked(force=True)

    def _persist_locked(self, force: bool = False) -> None:
        if self.output_dir is None:
            return
        now = time.monotonic()
        if not force and now - self._last_persist < 0.35:
            return
        state_file = self._state_file
        state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_file.with_suffix(".json.tmp")
        payload = {
            "schema_version": 1,
            "updated_at": _now(),
            "tasks": [task.as_json() for task in self._tasks.values()],
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(state_file)
        self._last_persist = now

    def _next_task_locked(self) -> QueueTask | None:
        if any(task.status == "blocked" for task in self._tasks.values()):
            return None
        queued = sorted(
            (task for task in self._tasks.values() if task.status == "queued"),
            key=lambda item: item.created_at,
        )
        return queued[0] if queued else None

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=0.5)
            self._wake.clear()
            while not self._stop.is_set():
                with self._lock:
                    if self.output_dir is None:
                        break
                    task = self._next_task_locked()
                    if task is None:
                        break
                    task.status = "preparing"
                    task.detail = "正在读取图片列表"
                    task.error = None
                    task.updated_at = _now()
                    self._running_id = task.id
                    self._persist_locked(force=True)

                try:
                    book, chapter = task.to_book_and_chapter()
                    downloader = ChapterDownloader(
                        client=self.client,
                        output_dir=self._require_directory(),
                        workers=self.workers,
                    )

                    def report(
                        stage: str,
                        current: int,
                        total: int,
                        detail: str,
                    ) -> None:
                        with self._lock:
                            live_task = self._tasks.get(task.id)
                            if not live_task:
                                return
                            live_task.status = stage
                            live_task.current = current
                            live_task.total = total
                            live_task.detail = detail
                            live_task.updated_at = _now()
                            self._persist_locked(
                                force=stage in {"packing", "completed"}
                                or (total > 0 and current == total)
                            )

                    archive, _ = downloader.download_chapter(
                        book,
                        chapter,
                        progress_callback=report,
                    )
                    with self._lock:
                        live_task = self._tasks.get(task.id)
                        if live_task:
                            live_task.status = "completed"
                            live_task.detail = "下载完成"
                            live_task.archive_path = str(archive)
                            live_task.error = None
                            live_task.updated_at = _now()
                            self._persist_locked(force=True)
                except AntiRobotRequired as exc:
                    with self._lock:
                        live_task = self._tasks.get(task.id)
                        if live_task:
                            live_task.status = "blocked"
                            live_task.detail = "等待人机验证"
                            live_task.error = str(exc)
                            live_task.verification_url = exc.url
                            live_task.updated_at = _now()
                            self._persist_locked(force=True)
                except Exception as exc:
                    with self._lock:
                        live_task = self._tasks.get(task.id)
                        if live_task:
                            live_task.status = "failed"
                            live_task.detail = "下载失败"
                            live_task.error = str(exc)
                            live_task.updated_at = _now()
                            self._persist_locked(force=True)
                finally:
                    with self._lock:
                        self._running_id = None
