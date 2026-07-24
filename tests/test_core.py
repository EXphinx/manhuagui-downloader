from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from manhuagui_downloader.cli import parse_selection
from manhuagui_downloader.downloader import ChapterDownloader, safe_filename
from manhuagui_downloader.models import Book, Chapter
from manhuagui_downloader.server import _parent_exists
from manhuagui_downloader.site import normalize_book_url


class SelectionTests(unittest.TestCase):
    def test_mixed_ranges(self) -> None:
        self.assertEqual(parse_selection("1, 3-5, 8", 10), [1, 3, 4, 5, 8])

    def test_all(self) -> None:
        self.assertEqual(parse_selection("all", 3), [1, 2, 3])

    def test_duplicate_values_are_removed(self) -> None:
        self.assertEqual(parse_selection("1-3,2,3", 5), [1, 2, 3])

    def test_out_of_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_selection("1-6", 5)

    def test_reverse_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_selection("5-2", 5)


class UtilityTests(unittest.TestCase):
    def test_mobile_url_is_normalized(self) -> None:
        self.assertEqual(
            normalize_book_url("https://m.manhuagui.com/comic/1325/"),
            ("1325", "https://www.manhuagui.com/comic/1325/"),
        )

    def test_filename_is_sanitized(self) -> None:
        self.assertEqual(safe_filename('a/b:c*?"'), "a_b_c___")

    def test_windows_reserved_filename_is_prefixed(self) -> None:
        self.assertEqual(safe_filename("CON.txt"), "_CON.txt")

    def test_filename_length_limits_windows_paths(self) -> None:
        self.assertEqual(len(safe_filename("a" * 200)), 80)

    def test_current_parent_process_is_detected_without_terminating_it(self) -> None:
        self.assertTrue(_parent_exists(os.getpid()))

    def test_chapter_is_packed_and_existing_zip_is_reused(self) -> None:
        class FakeImageClient:
            def fetch_chapter_images(
                self,
                _chapter: Chapter,
                _book_url: str,
            ) -> list[str]:
                return [
                    "https://img.example/one.jpg",
                    "https://img.example/two.png",
                ]

        book = Book(
            book_id="1",
            title="测试漫画",
            url="https://www.manhuagui.com/comic/1/",
            chapters=(),
        )
        chapter = Chapter(
            index=1,
            chapter_id="10",
            title="第01话",
            url="https://www.manhuagui.com/comic/1/10.html",
        )
        with tempfile.TemporaryDirectory() as temporary:
            downloader = ChapterDownloader(
                FakeImageClient(),  # type: ignore[arg-type]
                Path(temporary),
                workers=2,
            )
            events: list[tuple[str, int, int, str]] = []

            def write_page(
                _url: str,
                destination: Path,
                _referer: str,
            ) -> bool:
                destination.write_bytes(b"image")
                return False

            with patch.object(
                downloader,
                "_download_page",
                side_effect=write_page,
            ):
                archive, skipped = downloader.download_chapter(
                    book,
                    chapter,
                    progress_callback=lambda *event: events.append(event),
                )

            self.assertFalse(skipped)
            self.assertEqual(events[-1][:3], ("completed", 2, 2))
            with zipfile.ZipFile(archive) as result:
                self.assertEqual(result.namelist(), ["001.jpg", "002.png"])

            existing, skipped = downloader.download_chapter(book, chapter)
            self.assertTrue(skipped)
            self.assertEqual(existing, archive)


if __name__ == "__main__":
    unittest.main()
