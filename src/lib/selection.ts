import type { ChapterRow } from "./types";

export type ChapterFilter = "all" | "available" | "downloaded" | "selected";

export function filterChapters(
  chapters: ChapterRow[],
  query: string,
  filter: ChapterFilter,
  selected: ReadonlySet<number>,
): ChapterRow[] {
  const normalized = query.trim().toLocaleLowerCase("zh-CN");
  return chapters.filter((chapter) => {
    const matchesQuery =
      !normalized ||
      chapter.title.toLocaleLowerCase("zh-CN").includes(normalized) ||
      String(chapter.index).includes(normalized);
    if (!matchesQuery) return false;
    if (filter === "available") {
      return !chapter.downloaded && !chapter.task_status;
    }
    if (filter === "downloaded") return chapter.downloaded;
    if (filter === "selected") return selected.has(chapter.index);
    return true;
  });
}

export function inclusiveRange(
  start: number,
  end: number,
  maximum: number,
): Set<number> {
  const normalizedStart = Math.max(1, Math.min(start, maximum));
  const normalizedEnd = Math.max(1, Math.min(end, maximum));
  if (normalizedStart > normalizedEnd) return new Set();
  return new Set(
    Array.from(
      { length: normalizedEnd - normalizedStart + 1 },
      (_, index) => normalizedStart + index,
    ),
  );
}
