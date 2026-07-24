export type TaskStatus =
  | "queued"
  | "preparing"
  | "downloading"
  | "packing"
  | "blocked"
  | "completed"
  | "failed";

export interface ChapterRow {
  index: number;
  chapter_id: string;
  title: string;
  url: string;
  downloaded: boolean;
  task_status: TaskStatus | null;
}

export interface InspectedBook {
  book_id: string;
  title: string;
  url: string;
  chapters: ChapterRow[];
}

export interface Inspection {
  inspection_id: string;
  book: InspectedBook;
}

export interface QueueTask {
  id: string;
  book_id: string;
  book_title: string;
  book_url: string;
  chapter_id: string;
  chapter_index: number;
  chapter_title: string;
  chapter_url: string;
  status: TaskStatus;
  current: number;
  total: number;
  detail: string;
  error: string | null;
  verification_url: string | null;
  archive_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppSettings {
  download_directory: string | null;
  running: boolean;
}

export interface CreateTasksResult {
  created: QueueTask[];
  created_count: number;
  skipped_count: number;
}

export interface APIErrorPayload {
  error: {
    code: string;
    message: string;
    verification_url?: string;
  };
}
