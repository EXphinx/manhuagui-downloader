import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Download, RefreshCw } from "lucide-react";
import { APIError, api, waitForBackend } from "./lib/api";
import {
  chooseDirectory,
  rememberDirectory,
  savedDirectory,
} from "./lib/desktop";
import type { Inspection, QueueTask } from "./lib/types";
import { AppHeader } from "./components/AppHeader";
import { ChapterTable } from "./components/ChapterTable";
import { DirectoryGate } from "./components/DirectoryGate";
import { LinkInspector } from "./components/LinkInspector";
import { TaskQueue } from "./components/TaskQueue";
import {
  VerificationDialog,
  type VerificationRequest,
} from "./components/VerificationDialog";
import {
  ToastRegion,
  type ToastMessage,
} from "./components/ToastRegion";
import { Button } from "./components/ui/button";

type BootState = "starting" | "ready" | "failed";

export function App() {
  const [bootState, setBootState] = useState<BootState>("starting");
  const [bootError, setBootError] = useState<string | null>(null);
  const [directory, setDirectory] = useState<string | null>(null);
  const [choosingDirectory, setChoosingDirectory] = useState(false);
  const [directoryError, setDirectoryError] = useState<string | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [lastUrl, setLastUrl] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [creating, setCreating] = useState(false);
  const [tasks, setTasks] = useState<QueueTask[]>([]);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const [verification, setVerification] =
    useState<VerificationRequest | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastId = useRef(0);

  const pushToast = useCallback(
    (
      tone: ToastMessage["tone"],
      title: string,
      description?: string,
    ) => {
      const id = ++toastId.current;
      setToasts((current) => [...current, { id, tone, title, description }]);
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
      }, 4800);
    },
    [],
  );

  const refreshTasks = useCallback(async () => {
    if (!directory) return;
    try {
      setTasks(await api.tasks());
    } catch (reason) {
      if (reason instanceof APIError && reason.code === "directory_required") {
        setDirectory(null);
      }
    }
  }, [directory]);

  const connect = useCallback(async () => {
    setBootState("starting");
    setBootError(null);
    try {
      await waitForBackend();
      const settings = await api.settings();
      if (settings.download_directory) {
        setDirectory(settings.download_directory);
      } else {
        const remembered = savedDirectory();
        if (remembered) {
          const updated = await api.setDirectory(remembered);
          setDirectory(updated.download_directory);
        }
      }
      setBootState("ready");
    } catch (reason) {
      setBootError(reason instanceof Error ? reason.message : String(reason));
      setBootState("failed");
    }
  }, []);

  useEffect(() => {
    void connect();
  }, [connect]);

  useEffect(() => {
    if (!directory) return;
    void refreshTasks();
    const timer = window.setInterval(
      () => void refreshTasks(),
      document.hidden ? 1800 : 700,
    );
    return () => window.clearInterval(timer);
  }, [directory, refreshTasks]);

  useEffect(() => {
    setInspection((current) => {
      if (!current) return current;
      const latestTask = new Map<string, QueueTask>();
      for (const task of tasks) {
        if (
          task.book_id === current.book.book_id &&
          !latestTask.has(task.chapter_id)
        ) {
          latestTask.set(task.chapter_id, task);
        }
      }
      let changed = false;
      const chapters = current.book.chapters.map((chapter) => {
        const task = latestTask.get(chapter.chapter_id);
        let status = task?.status ?? null;
        let downloaded = chapter.downloaded;
        if (
          status === "completed" &&
          !downloaded &&
          chapter.task_status &&
          chapter.task_status !== "completed"
        ) {
          downloaded = true;
        } else if (status === "completed" && !downloaded) {
          status = null;
        }
        if (
          chapter.task_status === status &&
          chapter.downloaded === downloaded
        ) {
          return chapter;
        }
        changed = true;
        return { ...chapter, downloaded, task_status: status };
      });
      return changed
        ? { ...current, book: { ...current.book, chapters } }
        : current;
    });
  }, [tasks]);

  async function selectDirectory() {
    setChoosingDirectory(true);
    setDirectoryError(null);
    try {
      const path = await chooseDirectory(directory ?? savedDirectory());
      if (!path) return;
      const settings = await api.setDirectory(path);
      if (!settings.download_directory) {
        throw new Error("后端没有接受下载目录");
      }
      rememberDirectory(settings.download_directory);
      setDirectory(settings.download_directory);
      setInspection(null);
      setSelected(new Set());
      setTasks(await api.tasks());
    } catch (reason) {
      setDirectoryError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setChoosingDirectory(false);
    }
  }

  const inspectBook = useCallback(
    async (url: string) => {
      setInspecting(true);
      setLastUrl(url);
      try {
        const result = await api.inspectBook(url);
        setInspection(result);
        setSelected(new Set());
      } catch (reason) {
        if (
          reason instanceof APIError &&
          reason.code === "anti_robot" &&
          reason.verificationUrl
        ) {
          setVerification({
            url: reason.verificationUrl,
            retry: async () => {
              await inspectBook(url);
            },
          });
        } else {
          pushToast(
            "error",
            "没有读取到章节",
            reason instanceof Error ? reason.message : String(reason),
          );
        }
      } finally {
        setInspecting(false);
      }
    },
    [pushToast],
  );

  async function createTasks() {
    if (!inspection || selected.size === 0) return;
    setCreating(true);
    try {
      const result = await api.createTasks(
        inspection.inspection_id,
        [...selected].sort((a, b) => a - b),
      );
      setSelected(new Set());
      await refreshTasks();
      pushToast(
        "success",
        `已创建 ${result.created_count} 个任务`,
        result.skipped_count
          ? `${result.skipped_count} 章已经下载或已在队列中。`
          : "任务会按章节顺序自动执行。",
      );
    } catch (reason) {
      pushToast(
        "error",
        "任务没有创建",
        reason instanceof Error ? reason.message : String(reason),
      );
    } finally {
      setCreating(false);
    }
  }

  async function deleteTask(taskId: string) {
    setDeletingTaskId(taskId);
    try {
      await api.deleteTask(taskId);
      await refreshTasks();
      pushToast("info", "任务已取消", "临时图片会保留，重新添加后可以继续。");
    } catch (reason) {
      pushToast(
        "error",
        "任务没有取消",
        reason instanceof Error ? reason.message : String(reason),
      );
    } finally {
      setDeletingTaskId(null);
    }
  }

  const activeTaskCount = useMemo(
    () =>
      tasks.filter((task) =>
        ["queued", "preparing", "downloading", "packing", "blocked"].includes(
          task.status,
        ),
      ).length,
    [tasks],
  );

  if (bootState === "starting") {
    return (
      <main className="boot-screen" aria-live="polite">
        <span className="brand-mark brand-mark--large" aria-hidden="true">
          <Download />
        </span>
        <h1>正在启动本地下载服务</h1>
        <p>首次启动需要解压本地服务，通常会等待十几秒。</p>
        <div className="boot-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </main>
    );
  }

  if (bootState === "failed") {
    return (
      <main className="boot-screen">
        <div className="dialog-icon dialog-icon--danger" aria-hidden="true">
          <AlertTriangle />
        </div>
        <h1>本地下载服务没有启动</h1>
        <p>{bootError}</p>
        <Button variant="primary" onClick={() => void connect()}>
          <RefreshCw aria-hidden="true" />
          重新连接
        </Button>
      </main>
    );
  }

  if (!directory) {
    return (
      <DirectoryGate
        busy={choosingDirectory}
        error={directoryError}
        onChoose={() => void selectDirectory()}
      />
    );
  }

  return (
    <div className="app-shell">
      <AppHeader
        directory={directory}
        activeTasks={activeTaskCount}
        onChangeDirectory={() => void selectDirectory()}
      />
      <main className="workspace">
        <div className="workspace__main">
          <LinkInspector
            busy={inspecting}
            initialUrl={lastUrl}
            hasBook={Boolean(inspection)}
            onInspect={inspectBook}
          />
          {inspecting ? (
            <section className="chapter-skeleton" aria-label="正在读取章节">
              <div />
              <div />
              <div />
              <div />
            </section>
          ) : inspection ? (
            <ChapterTable
              book={inspection.book}
              selected={selected}
              creating={creating}
              onSelectedChange={setSelected}
              onCreateTasks={() => void createTasks()}
            />
          ) : (
            <section className="chapter-empty">
              <div className="chapter-empty__icon" aria-hidden="true">
                <Download />
              </div>
              <h2>从一个漫画链接开始</h2>
              <p>
                章节列表会显示序号、下载状态和筛选工具。完成选择后即可加入右侧队列。
              </p>
            </section>
          )}
        </div>
        <TaskQueue
          tasks={tasks}
          deletingTaskId={deletingTaskId}
          onDelete={deleteTask}
          onVerify={(url) =>
            setVerification({
              url,
              retry: refreshTasks,
            })
          }
        />
      </main>
      <VerificationDialog
        request={verification}
        onClose={() => setVerification(null)}
      />
      <ToastRegion
        messages={toasts}
        onDismiss={(id) =>
          setToasts((current) => current.filter((toast) => toast.id !== id))
        }
      />
    </div>
  );
}
