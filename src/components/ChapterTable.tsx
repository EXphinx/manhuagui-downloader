import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  CheckCheck,
  Download,
  Filter,
  Search,
  X,
} from "lucide-react";
import { filterChapters, inclusiveRange, type ChapterFilter } from "../lib/selection";
import type { InspectedBook } from "../lib/types";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { Select } from "./ui/select";

interface ChapterTableProps {
  book: InspectedBook;
  selected: ReadonlySet<number>;
  creating: boolean;
  onSelectedChange: (selected: Set<number>) => void;
  onCreateTasks: () => void;
}

function chapterState(
  downloaded: boolean,
  taskStatus: string | null,
): { label: string; className: string } {
  if (downloaded) return { label: "已下载", className: "state-chip--done" };
  if (taskStatus === "completed") {
    return { label: "已完成", className: "state-chip--done" };
  }
  if (taskStatus === "blocked") {
    return { label: "需验证", className: "state-chip--warning" };
  }
  if (taskStatus === "failed") {
    return { label: "失败", className: "state-chip--danger" };
  }
  if (taskStatus) return { label: "队列中", className: "state-chip--queued" };
  return { label: "未下载", className: "" };
}

export function ChapterTable({
  book,
  selected,
  creating,
  onSelectedChange,
  onCreateTasks,
}: ChapterTableProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ChapterFilter>("all");
  const [rangeStart, setRangeStart] = useState("1");
  const [rangeEnd, setRangeEnd] = useState(String(book.chapters.length));

  useEffect(() => {
    setQuery("");
    setFilter("all");
    setRangeStart("1");
    setRangeEnd(String(book.chapters.length));
  }, [book.book_id, book.chapters.length]);

  const visible = useMemo(
    () => filterChapters(book.chapters, query, filter, selected),
    [book.chapters, filter, query, selected],
  );
  const selectableVisible = visible.filter(
    (chapter) => !chapter.downloaded && !chapter.task_status,
  );
  const visibleSelected = selectableVisible.filter((chapter) =>
    selected.has(chapter.index),
  ).length;
  const allVisibleSelected =
    selectableVisible.length > 0 && visibleSelected === selectableVisible.length;
  const headerChecked: boolean | "indeterminate" =
    visibleSelected > 0 && !allVisibleSelected ? "indeterminate" : allVisibleSelected;

  function replaceSelection(values: Iterable<number>) {
    onSelectedChange(new Set(values));
  }

  function toggleChapter(index: number, checked: boolean) {
    const next = new Set(selected);
    if (checked) next.add(index);
    else next.delete(index);
    onSelectedChange(next);
  }

  function toggleVisible(checked: boolean) {
    const next = new Set(selected);
    for (const chapter of selectableVisible) {
      if (checked) next.add(chapter.index);
      else next.delete(chapter.index);
    }
    onSelectedChange(next);
  }

  function selectRange() {
    const selectableIndexes = new Set(
      book.chapters
        .filter((chapter) => !chapter.downloaded && !chapter.task_status)
        .map((chapter) => chapter.index),
    );
    replaceSelection(
      [...inclusiveRange(
        Number(rangeStart),
        Number(rangeEnd),
        book.chapters.length,
      )].filter((index) => selectableIndexes.has(index)),
    );
  }

  function invertVisible() {
    const next = new Set(selected);
    for (const chapter of selectableVisible) {
      if (next.has(chapter.index)) next.delete(chapter.index);
      else next.add(chapter.index);
    }
    onSelectedChange(next);
  }

  const available = book.chapters.filter(
    (chapter) => !chapter.downloaded && !chapter.task_status,
  );

  return (
    <section className="chapter-section" aria-labelledby="chapter-title">
      <div className="book-heading">
        <div>
          <h2 id="chapter-title">{book.title}</h2>
          <p>
            共 {book.chapters.length} 章 · {available.length} 章可加入任务
          </p>
        </div>
        <span className="book-id">ID {book.book_id}</span>
      </div>

      <div className="chapter-toolbar" aria-label="章节筛选和快捷选择">
        <div className="search-field">
          <Search aria-hidden="true" />
          <label className="sr-only" htmlFor="chapter-search">
            搜索章节
          </label>
          <input
            id="chapter-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索序号或章节标题"
          />
        </div>
        <Select
          value={filter}
          onValueChange={(value) => setFilter(value as ChapterFilter)}
          ariaLabel="筛选章节状态"
          options={[
            { value: "all", label: "全部章节" },
            { value: "available", label: "仅未下载" },
            { value: "downloaded", label: "仅已下载" },
            { value: "selected", label: "仅已选择" },
          ]}
        />
        <div className="toolbar-separator" aria-hidden="true" />
        <div className="range-picker">
          <label htmlFor="range-start">开始</label>
          <input
            id="range-start"
            type="number"
            min={1}
            max={book.chapters.length}
            value={rangeStart}
            onChange={(event) => setRangeStart(event.target.value)}
          />
          <span aria-hidden="true">—</span>
          <label htmlFor="range-end">结束</label>
          <input
            id="range-end"
            type="number"
            min={1}
            max={book.chapters.length}
            value={rangeEnd}
            onChange={(event) => setRangeEnd(event.target.value)}
          />
          <Button size="compact" onClick={selectRange}>
            选择范围
          </Button>
        </div>
      </div>

      <div className="quick-actions" aria-label="章节快捷选择">
        <Button
          variant="ghost"
          size="compact"
          onClick={() => replaceSelection(available.map((chapter) => chapter.index))}
        >
          <CheckCheck aria-hidden="true" />
          全部未下载
        </Button>
        <Button
          variant="ghost"
          size="compact"
          onClick={() =>
            replaceSelection(
              available.slice(-10).map((chapter) => chapter.index),
            )
          }
        >
          最近 10 章
        </Button>
        <Button variant="ghost" size="compact" onClick={invertVisible}>
          <ArrowDownUp aria-hidden="true" />
          反选筛选结果
        </Button>
        <Button variant="ghost" size="compact" onClick={() => replaceSelection([])}>
          <X aria-hidden="true" />
          清空选择
        </Button>
        <span className="filter-result">
          <Filter aria-hidden="true" />
          当前显示 {visible.length} 章
        </span>
      </div>

      <div className="chapter-table-wrap">
        <table className="chapter-table">
          <thead>
            <tr>
              <th className="chapter-table__check">
                <Checkbox
                  checked={headerChecked}
                  onCheckedChange={toggleVisible}
                  disabled={selectableVisible.length === 0}
                  aria-label={allVisibleSelected ? "取消选择当前结果" : "选择当前结果"}
                />
              </th>
              <th className="chapter-table__index">序号</th>
              <th>章节</th>
              <th className="chapter-table__state">状态</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((chapter) => {
              const state = chapterState(chapter.downloaded, chapter.task_status);
              const disabled = chapter.downloaded || Boolean(chapter.task_status);
              const checkboxId = `chapter-${book.book_id}-${chapter.chapter_id}`;
              return (
                <tr
                  key={chapter.chapter_id}
                  className={selected.has(chapter.index) ? "is-selected" : ""}
                >
                  <td className="chapter-table__check">
                    <Checkbox
                      id={checkboxId}
                      checked={selected.has(chapter.index)}
                      onCheckedChange={(checked) =>
                        toggleChapter(chapter.index, checked)
                      }
                      aria-label={`选择 ${chapter.title}`}
                      disabled={disabled}
                    />
                  </td>
                  <td className="chapter-table__index">
                    {String(chapter.index).padStart(
                      String(book.chapters.length).length,
                      "0",
                    )}
                  </td>
                  <td>
                    <label htmlFor={checkboxId} className={disabled ? "is-disabled" : ""}>
                      {chapter.title}
                    </label>
                  </td>
                  <td className="chapter-table__state">
                    <span className={`state-chip ${state.className}`}>
                      {state.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {visible.length === 0 ? (
          <div className="table-empty">
            <Search aria-hidden="true" />
            <p>没有符合当前条件的章节。</p>
            <Button
              variant="ghost"
              size="compact"
              onClick={() => {
                setQuery("");
                setFilter("all");
              }}
            >
              清除筛选
            </Button>
          </div>
        ) : null}
      </div>

      <div className="selection-bar" aria-live="polite">
        <div>
          <strong>{selected.size}</strong>
          <span>章已选择</span>
        </div>
        <Button
          variant="primary"
          onClick={onCreateTasks}
          disabled={selected.size === 0 || creating}
        >
          <Download aria-hidden="true" />
          {creating ? "正在创建任务…" : `创建 ${selected.size} 个任务`}
        </Button>
      </div>
    </section>
  );
}
