import { describe, expect, it } from "vitest";
import { filterChapters, inclusiveRange } from "./selection";
import type { ChapterRow } from "./types";

const chapters: ChapterRow[] = [
  {
    index: 1,
    chapter_id: "a",
    title: "第01卷",
    url: "https://example.test/1",
    downloaded: false,
    task_status: null,
  },
  {
    index: 2,
    chapter_id: "b",
    title: "特别篇",
    url: "https://example.test/2",
    downloaded: true,
    task_status: "completed",
  },
];

describe("chapter selection", () => {
  it("creates inclusive ranges", () => {
    expect([...inclusiveRange(2, 4, 10)]).toEqual([2, 3, 4]);
  });

  it("rejects a reversed range", () => {
    expect([...inclusiveRange(5, 2, 10)]).toEqual([]);
  });

  it("filters available chapters", () => {
    expect(filterChapters(chapters, "", "available", new Set())).toEqual([
      chapters[0],
    ]);
  });

  it("finds chapters by sequence", () => {
    expect(filterChapters(chapters, "2", "all", new Set())).toEqual([
      chapters[1],
    ]);
  });
});
