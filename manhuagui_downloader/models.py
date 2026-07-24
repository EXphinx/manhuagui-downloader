from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chapter:
    index: int
    chapter_id: str
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class Book:
    book_id: str
    title: str
    url: str
    chapters: tuple[Chapter, ...]

