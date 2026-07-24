import { Download, Folder, FolderOpen } from "lucide-react";
import { Button } from "./ui/button";
import { Tooltip } from "./ui/tooltip";

interface AppHeaderProps {
  directory: string;
  activeTasks: number;
  onChangeDirectory: () => void;
}

function shortPath(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  if (parts.length <= 3) return path;
  return `…/${parts.slice(-3).join("/")}`;
}

export function AppHeader({
  directory,
  activeTasks,
  onChangeDirectory,
}: AppHeaderProps) {
  return (
    <header className="app-header" data-tauri-drag-region>
      <div className="app-header__brand" data-tauri-drag-region>
        <span className="brand-mark" aria-hidden="true">
          <Download />
        </span>
        <span>漫画柜下载器</span>
      </div>
      <div className="app-header__meta">
        <span className="queue-summary" aria-live="polite">
          <span className={activeTasks > 0 ? "status-dot status-dot--active" : "status-dot"} />
          {activeTasks > 0 ? `${activeTasks} 个任务进行中` : "队列空闲"}
        </span>
        <Tooltip label={directory}>
          <Button
            variant="ghost"
            size="compact"
            onClick={onChangeDirectory}
            aria-label={`更换下载目录，当前目录 ${directory}`}
          >
            <Folder aria-hidden="true" />
            <span className="path-label">{shortPath(directory)}</span>
            <FolderOpen className="button__trailing-icon" aria-hidden="true" />
          </Button>
        </Tooltip>
      </div>
    </header>
  );
}
