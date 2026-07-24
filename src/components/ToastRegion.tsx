import { CircleCheck, CircleX, Info, X } from "lucide-react";
import { Button } from "./ui/button";

export interface ToastMessage {
  id: number;
  tone: "success" | "error" | "info";
  title: string;
  description?: string;
}

interface ToastRegionProps {
  messages: ToastMessage[];
  onDismiss: (id: number) => void;
}

const ICONS = {
  success: CircleCheck,
  error: CircleX,
  info: Info,
};

export function ToastRegion({ messages, onDismiss }: ToastRegionProps) {
  return (
    <div className="toast-region" aria-live="polite" aria-label="通知">
      {messages.map((message) => {
        const Icon = ICONS[message.tone];
        return (
          <div className={`toast toast--${message.tone}`} key={message.id}>
            <Icon aria-hidden="true" />
            <div>
              <strong>{message.title}</strong>
              {message.description ? <p>{message.description}</p> : null}
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="关闭通知"
              onClick={() => onDismiss(message.id)}
            >
              <X aria-hidden="true" />
            </Button>
          </div>
        );
      })}
    </div>
  );
}
