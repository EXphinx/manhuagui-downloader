import { useEffect, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import {
  closeVerificationWindow,
  isDesktopApp,
  openVerificationWindow,
  readVerificationCookies,
} from "../lib/desktop";
import { Button } from "./ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "./ui/dialog";

export interface VerificationRequest {
  url: string;
  retry: () => Promise<void>;
}

interface VerificationDialogProps {
  request: VerificationRequest | null;
  onClose: () => void;
}

export function VerificationDialog({
  request,
  onClose,
}: VerificationDialogProps) {
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setOpened(false);
    setBusy(false);
    setError(null);
  }, [request?.url]);

  async function openWindow() {
    if (!request) return;
    setError(null);
    try {
      await openVerificationWindow(request.url);
      setOpened(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  async function completeVerification() {
    if (!request) return;
    setBusy(true);
    setError(null);
    try {
      const cookies = await readVerificationCookies(request.url);
      if (cookies) await api.applyVerificationCookies(cookies);
      await closeVerificationWindow();
      onClose();
      await request.retry();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  function closeDialog() {
    void closeVerificationWindow().catch(() => undefined);
    onClose();
  }

  return (
    <Dialog
      open={Boolean(request)}
      onOpenChange={(open) => !open && closeDialog()}
    >
      <DialogContent>
        <div className="dialog-icon dialog-icon--warning" aria-hidden="true">
          <ShieldCheck />
        </div>
        <DialogTitle>漫画站点需要确认你是真人</DialogTitle>
        <DialogDescription>
          打开验证窗口，按页面提示完成操作。应用只会读取
          manhuagui.com 的验证 Cookie，然后重新执行刚才的请求。
        </DialogDescription>
        <ol className="verification-steps">
          <li>
            <span>1</span>
            <p>打开验证窗口并完成页面中的检查。</p>
          </li>
          <li>
            <span>2</span>
            <p>回到这里，点击“验证完成并重试”。</p>
          </li>
        </ol>
        {!isDesktopApp() ? (
          <p className="inline-message">
            当前是浏览器开发模式，无法自动读取浏览器 Cookie；完成验证后会直接重试。
          </p>
        ) : null}
        {error ? (
          <p className="inline-message inline-message--error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="dialog-actions dialog-actions--split">
          <Button onClick={openWindow}>
            <ExternalLink aria-hidden="true" />
            {opened ? "重新打开验证窗口" : "打开验证窗口"}
          </Button>
          <Button
            variant="primary"
            onClick={completeVerification}
            disabled={!opened || busy}
          >
            {busy ? "正在读取验证结果…" : "验证完成并重试"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
