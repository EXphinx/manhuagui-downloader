import { useMemo, useState } from "react";
import {
  CircleCheck,
  CircleX,
  Clock3,
  LoaderCircle,
  Package,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import type { QueueTask, TaskStatus } from "../lib/types";
import { Button } from "./ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "./ui/dialog";
import { Progress } from "./ui/progress";
import { Select } from "./ui/select";
import { Tooltip } from "./ui/tooltip";

type QueueFilter = "all" | "active" | "completed" | "failed";

const ACTIVE = new Set<TaskStatus>([
  "queued",
  "preparing",
  "downloading",
  "packing",
  "blocked",
]);

const STATUS_COPY: Record<
  TaskStatus,
  { label: string; className: string; icon: typeof Clock3 }
> = {
  queued: { label: "等待中", className: "queued", icon: Clock3 },
  preparing: { label: "读取中", className: "active", icon: LoaderCircle },
  downloading: { label: "下载中", className: "active", icon: LoaderCircle },
  packing: { label: "打包中", className: "active", icon: Package },
  blocked: { label: "需要验证", className: "blocked", icon: ShieldAlert },
  completed: { label: "已完成", className: "completed", icon: CircleCheck },
  failed: { label: "失败", className: "failed", icon: CircleX },
};

interface TaskQueueProps {
  tasks: QueueTask[];
  deletingTaskId: string | null;
  onDelete: (taskId: string) => Promise<void>;
  onVerify: (url: string) => void;
}

export function TaskQueue({
  tasks,
  deletingTaskId,
  onDelete,
  onVerify,
}: TaskQueueProps) {
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [confirmTask, setConfirmTask] = useState<QueueTask | null>(null);

  const filtered = useMemo(
    () =>
      tasks.filter((task) => {
        if (filter === "active") return ACTIVE.has(task.status);
        if (filter === "completed") return task.status === "completed";
        if (filter === "failed") return task.status === "failed";
        return true;
      }),
    [filter, tasks],
  );

  async function confirmDelete() {
    if (!confirmTask) return;
    await onDelete(confirmTask.id);
    setConfirmTask(null);
  }

  return (
    <aside className="task-queue" aria-labelledby="queue-title">
      <div className="task-queue__header">
        <div>
          <h2 id="queue-title">任务队列</h2>
          <p>{tasks.length ? `共 ${tasks.length} 个任务` : "等待创建任务"}</p>
        </div>
        <Select
          value={filter}
          onValueChange={(value) => setFilter(value as QueueFilter)}
          ariaLabel="筛选任务队列"
          options={[
            { value: "all", label: "全部任务" },
            { value: "active", label: "进行中" },
            { value: "completed", label: "已完成" },
            { value: "failed", label: "失败" },
          ]}
        />
      </div>

      <div className="task-list" aria-live="polite">
        {filtered.map((task) => {
          const status = STATUS_COPY[task.status];
          const StatusIcon = status.icon;
          const percent =
            task.total > 0 ? Math.round((task.current / task.total) * 100) : 0;
          const removable = ["queued", "blocked", "failed"].includes(task.status);
          return (
            <article className="task-row" key={task.id}>
              <div className="task-row__topline">
                <span className={`task-status task-status--${status.className}`}>
                  <StatusIcon
                    className={
                      ["preparing", "downloading"].includes(task.status)
                        ? "is-spinning"
                        : ""
                    }
                    aria-hidden="true"
                  />
                  {status.label}
                </span>
                {removable ? (
                  <Tooltip label="取消任务">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setConfirmTask(task)}
                      aria-label={`取消 ${task.chapter_title}`}
                      disabled={deletingTaskId === task.id}
                    >
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </Tooltip>
                ) : null}
              </div>
              <h3>{task.chapter_title}</h3>
              <p className="task-row__book">{task.book_title}</p>
              {task.status === "downloading" || task.status === "packing" ? (
                <div className="task-progress">
                  <Progress
                    value={percent}
                    label={`${task.chapter_title} 下载进度 ${percent}%`}
                  />
                  <span>
                    {task.status === "packing"
                      ? "正在创建 ZIP"
                      : `${task.current} / ${task.total}`}
                  </span>
                </div>
              ) : (
                <p
                  className={`task-detail ${
                    task.error ? "task-detail--error" : ""
                  }`}
                >
                  {task.error || task.detail}
                </p>
              )}
              {task.status === "blocked" && task.verification_url ? (
                <Button
                  variant="secondary"
                  size="compact"
                  className="task-row__verify"
                  onClick={() => onVerify(task.verification_url!)}
                >
                  <ShieldAlert aria-hidden="true" />
                  完成人机验证
                </Button>
              ) : null}
            </article>
          );
        })}
        {filtered.length === 0 ? (
          <div className="queue-empty">
            <Clock3 aria-hidden="true" />
            <h3>{tasks.length ? "此筛选下没有任务" : "任务会显示在这里"}</h3>
            <p>
              {tasks.length
                ? "切换筛选条件查看其他任务。"
                : "读取漫画章节并完成选择后，任务会自动依次下载。"}
            </p>
          </div>
        ) : null}
      </div>

      <Dialog
        open={Boolean(confirmTask)}
        onOpenChange={(open) => !open && setConfirmTask(null)}
      >
        <DialogContent className="dialog-content--small">
          <DialogTitle>取消“{confirmTask?.chapter_title}”任务？</DialogTitle>
          <DialogDescription>
            任务会从队列中删除。已经下载的临时图片会保留，再次添加该章节时可以继续。
          </DialogDescription>
          <div className="dialog-actions">
            <Button onClick={() => setConfirmTask(null)}>保留任务</Button>
            <Button
              variant="danger"
              onClick={confirmDelete}
              disabled={deletingTaskId === confirmTask?.id}
            >
              {deletingTaskId === confirmTask?.id ? "正在取消…" : "取消任务"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
