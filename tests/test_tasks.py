from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from manhuagui_downloader.models import Book, Chapter
from manhuagui_downloader.site import ManhuaGuiError
from manhuagui_downloader.tasks import TaskManager


class FakeClient:
    def __init__(self) -> None:
        self.cookie = ""
        self.book = Book(
            book_id="1325",
            title="测试漫画",
            url="https://www.manhuagui.com/comic/1325/",
            chapters=(
                Chapter(
                    index=1,
                    chapter_id="1001",
                    title="第01卷",
                    url="https://www.manhuagui.com/comic/1325/1001.html",
                ),
                Chapter(
                    index=2,
                    chapter_id="1002",
                    title="第02卷",
                    url="https://www.manhuagui.com/comic/1325/1002.html",
                ),
            ),
        )

    def fetch_book(self, _url: str) -> Book:
        return self.book

    def set_cookie_header(self, value: str) -> None:
        self.cookie = value


class TaskManagerTests(unittest.TestCase):
    def test_queue_is_saved_and_restored_from_download_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            client = FakeClient()
            manager = TaskManager(client)  # type: ignore[arg-type]
            manager.close()
            manager.set_directory(str(directory))

            inspection = manager.inspect_book(client.book.url)
            created = manager.create_tasks(inspection["inspection_id"], [1, 2])

            self.assertEqual(created["created_count"], 2)
            self.assertEqual(
                [task["status"] for task in manager.list_tasks()],
                ["queued", "queued"],
            )

            state_file = directory / ".manhuagui" / "tasks.json"
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["tasks"]), 2)

            restored = TaskManager(FakeClient())  # type: ignore[arg-type]
            restored.close()
            restored.set_directory(str(directory))
            self.assertEqual(len(restored.list_tasks()), 2)

    def test_verification_cookies_requeue_blocked_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            client = FakeClient()
            manager = TaskManager(client)  # type: ignore[arg-type]
            manager.close()
            manager.set_directory(temporary)
            inspection = manager.inspect_book(client.book.url)
            created = manager.create_tasks(inspection["inspection_id"], [1])
            task_id = created["created"][0]["id"]

            with manager._lock:
                manager._tasks[task_id].status = "blocked"
                manager._tasks[task_id].verification_url = client.book.url

            retried = manager.apply_verification_cookies("cf_clearance=test")

            self.assertEqual(retried, 1)
            self.assertEqual(client.cookie, "cf_clearance=test")
            self.assertEqual(manager.list_tasks()[0]["status"], "queued")

    def test_missing_completed_zip_can_be_added_again(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            client = FakeClient()
            manager = TaskManager(client)  # type: ignore[arg-type]
            manager.close()
            manager.set_directory(temporary)
            inspection = manager.inspect_book(client.book.url)
            created = manager.create_tasks(inspection["inspection_id"], [1])
            task_id = created["created"][0]["id"]
            with manager._lock:
                manager._tasks[task_id].status = "completed"
                manager._tasks[task_id].archive_path = str(
                    Path(temporary) / "missing.zip"
                )

            refreshed = manager.inspect_book(client.book.url)
            first_chapter = refreshed["book"]["chapters"][0]
            self.assertFalse(first_chapter["downloaded"])
            self.assertIsNone(first_chapter["task_status"])
            recreated = manager.create_tasks(refreshed["inspection_id"], [1])
            self.assertEqual(recreated["created_count"], 1)

    def test_invalid_state_does_not_replace_current_directory(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            manager = TaskManager(FakeClient())  # type: ignore[arg-type]
            manager.close()
            manager.set_directory(first)
            state_dir = Path(second) / ".manhuagui"
            state_dir.mkdir()
            (state_dir / "tasks.json").write_text("{broken", encoding="utf-8")

            with self.assertRaises(ManhuaGuiError):
                manager.set_directory(second)

            self.assertEqual(
                manager.settings()["download_directory"],
                str(Path(first).resolve()),
            )


if __name__ == "__main__":
    unittest.main()
