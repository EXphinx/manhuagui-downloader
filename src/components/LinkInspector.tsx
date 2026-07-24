import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowRight, Link2, ListChecks } from "lucide-react";
import { Button } from "./ui/button";

interface LinkInspectorProps {
  busy: boolean;
  initialUrl?: string;
  hasBook: boolean;
  onInspect: (url: string) => Promise<void>;
}

export function LinkInspector({
  busy,
  initialUrl = "",
  hasBook,
  onInspect,
}: LinkInspectorProps) {
  const [url, setUrl] = useState(initialUrl);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!hasBook) inputRef.current?.focus();
  }, [hasBook]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!url.trim() || busy) return;
    await onInspect(url.trim());
  }

  return (
    <section className="link-inspector" aria-labelledby="new-task-title">
      <div className="section-heading">
        <div>
          <h1 id="new-task-title">创建下载任务</h1>
          <p>粘贴漫画详情页链接，读取章节后选择需要下载的内容。</p>
        </div>
        {hasBook ? (
          <span className="quiet-badge">
            <ListChecks aria-hidden="true" />
            章节已读取
          </span>
        ) : null}
      </div>
      <form className="url-form" onSubmit={submit}>
        <label htmlFor="comic-url">漫画链接</label>
        <div className="url-form__row">
          <span className="input-icon" aria-hidden="true">
            <Link2 />
          </span>
          <input
            ref={inputRef}
            id="comic-url"
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://m.manhuagui.com/comic/1325/"
            autoComplete="url"
            spellCheck={false}
            disabled={busy}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={busy || !url.trim()}
          >
            {busy ? "正在读取章节…" : hasBook ? "重新读取" : "获取章节"}
            {!busy ? <ArrowRight aria-hidden="true" /> : null}
          </Button>
        </div>
      </form>
    </section>
  );
}
