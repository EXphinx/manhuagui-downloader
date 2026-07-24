from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .downloader import ChapterDownloader, safe_filename
from .models import Chapter
from .site import ManhuaGuiClient, ManhuaGuiError


def parse_selection(expression: str, chapter_count: int) -> list[int]:
    value = expression.strip().lower()
    if value in {"all", "*", "全部"}:
        return list(range(1, chapter_count + 1))
    if not value:
        raise ValueError("请选择至少一个章节")

    selected: set[int] = set()
    for part in value.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            pieces = [piece.strip() for piece in part.split("-", 1)]
            if len(pieces) != 2 or not all(piece.isdigit() for piece in pieces):
                raise ValueError(f"无效范围: {part}")
            start, end = map(int, pieces)
            if start > end:
                raise ValueError(f"范围起点不能大于终点: {part}")
            selected.update(range(start, end + 1))
        elif part.isdigit():
            selected.add(int(part))
        else:
            raise ValueError(f"无效章节编号: {part}")

    if not selected:
        raise ValueError("请选择至少一个章节")
    invalid = sorted(index for index in selected if not 1 <= index <= chapter_count)
    if invalid:
        raise ValueError(
            f"章节编号超出范围 1-{chapter_count}: "
            + ", ".join(map(str, invalid))
        )
    return sorted(selected)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manhuagui",
        description="下载 ManhuaGui 漫画章节，支持范围选择、断点续传和 ZIP 打包。",
    )
    parser.add_argument("url", nargs="?", help="漫画详情页链接")
    parser.add_argument(
        "-s",
        "--select",
        metavar="RANGE",
        help="章节范围，例如 1-5、1,3,8-10 或 all",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("downloads"),
        help="下载目录（默认: ./downloads）",
    )
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=4,
        help="单章节并发下载数（默认: 4）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="只显示章节列表，不下载",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _print_chapters(title: str, chapters: tuple[Chapter, ...]) -> None:
    width = len(str(len(chapters)))
    print(f"\n{title}，共 {len(chapters)} 章：")
    for chapter in chapters:
        print(f"  {chapter.index:>{width}}. {chapter.title}")


def run(args: argparse.Namespace) -> int:
    input_url = args.url or input("请输入 ManhuaGui 漫画链接: ").strip()
    client = ManhuaGuiClient()
    print("正在读取漫画信息…")
    book = client.fetch_book(input_url)
    _print_chapters(book.title, book.chapters)

    if args.list:
        return 0

    selection = args.select
    while selection is None:
        selection = input(
            "\n选择章节（如 1-5、1,3,8-10，输入 all 下载全部）: "
        ).strip()
        try:
            indices = parse_selection(selection, len(book.chapters))
        except ValueError as exc:
            print(f"选择无效: {exc}", file=sys.stderr)
            selection = None
    if selection is not None:
        indices = parse_selection(selection, len(book.chapters))

    chapters = [book.chapters[index - 1] for index in indices]
    print(f"\n准备下载 {len(chapters)} 个章节，输出目录: {args.output.resolve()}")
    downloader = ChapterDownloader(
        client=client,
        output_dir=args.output,
        workers=args.workers,
    )
    archives = downloader.download_book(book, chapters)
    result_dir = args.output / safe_filename(book.title, book.book_id)
    print(f"\n完成，共 {len(archives)} 个 ZIP：{result_dir.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers 必须大于 0")
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\n已中止。再次运行相同命令会继续未完成的图片。", file=sys.stderr)
        return 130
    except (ManhuaGuiError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
