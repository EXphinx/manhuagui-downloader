import { Database, FolderOpen, ShieldCheck } from "lucide-react";
import { Button } from "./ui/button";

interface DirectoryGateProps {
  busy: boolean;
  error: string | null;
  onChoose: () => void;
}

export function DirectoryGate({
  busy,
  error,
  onChoose,
}: DirectoryGateProps) {
  return (
    <main className="directory-gate">
      <section className="directory-gate__panel" aria-labelledby="directory-title">
        <div className="brand-mark brand-mark--large" aria-hidden="true">
          <Database />
        </div>
        <div className="directory-gate__copy">
          <p className="app-name">漫画柜下载器</p>
          <h1 id="directory-title">先选择下载目录</h1>
          <p>
            ZIP、未完成图片和任务进度都会保存在这里。下次选择同一目录，应用会继续未完成的任务。
          </p>
        </div>
        <Button
          variant="primary"
          onClick={onChoose}
          disabled={busy}
          className="directory-gate__action"
        >
          <FolderOpen aria-hidden="true" />
          {busy ? "正在打开目录选择器…" : "选择下载目录"}
        </Button>
        {error ? (
          <p className="inline-message inline-message--error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="directory-gate__note">
          <ShieldCheck aria-hidden="true" />
          <span>任务数据仅写入你选择的本地目录。</span>
        </div>
      </section>
    </main>
  );
}
