import type {
  APIErrorPayload,
  AppSettings,
  CreateTasksResult,
  Inspection,
  QueueTask,
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:48135/api";

export class APIError extends Error {
  readonly status: number;
  readonly code: string;
  readonly verificationUrl?: string;

  constructor(status: number, payload: APIErrorPayload) {
    super(payload.error.message);
    this.name = "APIError";
    this.status = status;
    this.code = payload.error.code;
    this.verificationUrl = payload.error.verification_url;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  const payload = (await response.json()) as T | APIErrorPayload;
  if (!response.ok) {
    throw new APIError(response.status, payload as APIErrorPayload);
  }
  return payload as T;
}

export async function waitForBackend(
  attempts = 160,
  delay = 250,
): Promise<void> {
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        cache: "no-store",
      });
      if (response.ok) return;
    } catch {
      // The sidecar can take a moment to unpack on first launch.
    }
    await new Promise((resolve) => window.setTimeout(resolve, delay));
  }
  throw new Error("本地下载服务没有启动");
}

export const api = {
  settings: () => request<AppSettings>("/settings"),

  setDirectory: (path: string) =>
    request<AppSettings>("/settings/directory", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  inspectBook: (url: string) =>
    request<Inspection>("/books/inspect", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  tasks: async () => {
    const result = await request<{ tasks: QueueTask[] }>("/tasks");
    return result.tasks;
  },

  createTasks: (inspectionId: string, chapterIndexes: number[]) =>
    request<CreateTasksResult>("/tasks", {
      method: "POST",
      body: JSON.stringify({
        inspection_id: inspectionId,
        chapter_indexes: chapterIndexes,
      }),
    }),

  deleteTask: (taskId: string) =>
    request<{ deleted: string }>(`/tasks/${encodeURIComponent(taskId)}`, {
      method: "DELETE",
    }),

  applyVerificationCookies: (cookie: string) =>
    request<{ retried_tasks: number }>("/anti-robot/cookies", {
      method: "POST",
      body: JSON.stringify({ cookie }),
    }),
};
