import * as React from "react";
import { Send, Loader2, CornerDownLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ChatInputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (question: string) => void;
  isSending?: boolean;
  selectedDocumentsCount?: number;
}

const MAX_TEXTAREA_HEIGHT = 160;

/**
 * [SP5-03.3] Ô nhập câu hỏi (ChatInputBox / ChatInput):
 * - Tự động giãn chiều cao (auto-resize textarea) khi nhập nhiều dòng.
 * - Nhấn Enter để gửi câu hỏi ngay; nhấn Shift+Enter để xuống dòng.
 * - Tự động khóa nút gửi khi câu hỏi trống hoặc khi hệ thống đang xử lý (isSending).
 */
export function ChatInputBox({
  value,
  onChange,
  onSubmit,
  isSending = false,
  selectedDocumentsCount = 0,
}: ChatInputBoxProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  const adjustTextareaHeight = React.useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const nextHeight = Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT);
    el.style.height = `${Math.max(42, nextHeight)}px`;
  }, []);

  React.useEffect(() => {
    adjustTextareaHeight();
  }, [value, adjustTextareaHeight]);

  const handleTriggerSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isSending) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Nhấn Enter (không giữ Shift) -> Gửi câu hỏi ([SP5-03.3])
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleTriggerSubmit();
    }
  };

  const isSubmitDisabled = !value.trim() || isSending;

  return (
    <div className="border-t border-border-default bg-bg-surface px-4 py-3.5">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleTriggerSubmit();
        }}
        className="mx-auto max-w-3xl"
      >
        <div className="flex items-end gap-2.5 rounded-2xl border border-border-default bg-bg-app px-3.5 py-2 transition-colors focus-within:border-primary focus-within:bg-bg-surface focus-within:ring-2 focus-within:ring-primary/15">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            disabled={isSending}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedDocumentsCount > 0
                ? `Nhập câu hỏi tra cứu trên ${selectedDocumentsCount} tài liệu đã chọn... (Enter để gửi, Shift+Enter xuống dòng)`
                : "Hãy tích chọn ít nhất 1 tài liệu ở cột bên trái trước khi đặt câu hỏi..."
            }
            className="max-h-[160px] min-h-[28px] flex-1 resize-none bg-transparent py-1 text-[15px] leading-relaxed text-text-primary placeholder:text-text-muted focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          />

          <Button
            type="submit"
            disabled={isSubmitDisabled}
            className="h-9 shrink-0 rounded-xl px-4"
          >
            {isSending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang trả lời...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Gửi</span>
              </>
            )}
          </Button>
        </div>

        <div className="mt-1.5 flex items-center justify-between px-1 text-[11px] text-text-muted">
          <span>
            AI chỉ sử dụng thông tin trong tài liệu đã chọn và trích dẫn nguồn{" "}
            <strong className="font-mono text-primary">[S1]</strong>,{" "}
            <strong className="font-mono text-primary">[S2]</strong>.
          </span>
          <span className="hidden items-center gap-1 sm:inline-flex">
            <CornerDownLeft className="h-3 w-3" />
            <span>Enter gửi • Shift+Enter xuống dòng</span>
          </span>
        </div>
      </form>
    </div>
  );
}

export const ChatInput = ChatInputBox;

