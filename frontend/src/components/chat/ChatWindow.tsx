import * as React from "react";
import { Bot, Sparkles, Loader2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyChatState } from "@/components/chat/EmptyChatState";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInputBox } from "@/components/chat/ChatInputBox";
import { useToast } from "@/hooks/useToast";
import { useDocumentsStore } from "@/features/documents/useDocuments";
import { useChatSession } from "@/features/chat/useChatSession";
import {
  useActiveCitation,
  SAMPLE_CITATIONS,
} from "@/features/chat/useActiveCitation";
import { ApiClientError } from "@/services/api-client";
import { sendChatMessage } from "@/services/chat-api";
import type { IMessage } from "@/types";

/**
 * [SP5-03.4] Hiệu ứng khung xương chờ (Skeleton / Typing Indicator)
 * hiển thị khi hệ thống đang truy xuất ngữ nghĩa Top-K và tổng hợp câu trả lời.
 */
export function ChatTypingSkeleton() {
  return (
    <div
      aria-label="Trợ lý AI đang tổng hợp câu trả lời"
      className="flex items-start justify-start gap-2.5"
    >
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-white shadow-2xs">
        <Bot className="h-4 w-4 animate-pulse" />
      </div>

      <div className="w-full max-w-[78%] rounded-2xl rounded-tl-xs border border-border-default bg-bg-app px-4 py-3.5 shadow-2xs">
        <div className="flex items-center gap-2 text-xs font-medium text-primary">
          <Sparkles className="h-3.5 w-3.5 animate-spin" />
          <span>
            Đang truy xuất đoạn văn Top-K từ ChromaDB & tổng hợp câu trả lời...
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </span>
        </div>

        {/* Khung xương Shimmer (Skeleton lines) */}
        <div className="mt-3 space-y-2">
          <div className="h-3.5 w-[92%] animate-pulse rounded-md bg-slate-200" />
          <div className="h-3.5 w-[80%] animate-pulse rounded-md bg-slate-200" />
          <div className="h-3.5 w-[64%] animate-pulse rounded-md bg-slate-200" />
        </div>
      </div>
    </div>
  );
}

/**
 * [SP5-03.1 -> SP5-03.4 & SP5-05.3 & SP5-05.4] Không gian nhắn tin hỏi đáp trung tâm (ChatWindow / MessageList):
 * - Tự động cuộn mượt xuống cuối (Auto-scroll) khi có tin nhắn mới hoặc khi đang chờ phản hồi.
 * - Hiển thị EmptyChatState kèm câu hỏi gợi ý khi chưa có tin nhắn.
 * - Hiển thị trạng thái tải lại lịch sử trò chuyện (isLoadingHistory) khi người dùng chọn phiên chat cũ.
 * - Hiển thị Toast Notification rõ ràng khi gặp lỗi kết nối mạng hoặc lỗi xử lý từ LLM/Backend.
 */
export function ChatWindow() {
  const { toast } = useToast();
  const { selectedDocumentIds, documents } = useDocumentsStore();
  const {
    messages,
    activeConversationId,
    isSending,
    isLoadingHistory,
    addMessage,
    upsertConversation,
    setIsSending,
  } = useChatSession();
  const { activeCitation, openCitation, setActiveCitation } =
    useActiveCitation();

  const [questionInput, setQuestionInput] = React.useState("");
  const bottomAnchorRef = React.useRef<HTMLDivElement | null>(null);

  // [SP5-03.1] Tự động cuộn xuống cuối danh sách mỗi khi có tin nhắn mới hoặc trạng thái chờ thay đổi
  React.useEffect(() => {
    bottomAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isSending]);

  const handleSendQuestion = async (rawQuestion: string) => {
    const trimmed = rawQuestion.trim();
    if (!trimmed || isSending) return;

    if (selectedDocumentIds.length === 0) {
      toast({
        title: "Chưa chọn tài liệu tra cứu",
        description:
          "Vui lòng tích chọn ít nhất 1 tài liệu ở Sidebar bên trái trước khi đặt câu hỏi.",
        variant: "warning",
      });
      return;
    }

    const tempConvId = activeConversationId || `conv-${Date.now()}`;
    const userMsg: IMessage = {
      id: `user-${Date.now()}`,
      conversation_id: tempConvId,
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    addMessage(userMsg);
    setQuestionInput("");
    setIsSending(true);

    try {
      const isRealUuidDocs = selectedDocumentIds.every(
        (id) => !id.startsWith("doc-demo-") && !id.startsWith("temp-")
      );
      const isRealConvId =
        activeConversationId &&
        !activeConversationId.startsWith("conv-demo-") &&
        !activeConversationId.startsWith("conv-");

      const response = await sendChatMessage({
        question: trimmed,
        document_ids: isRealUuidDocs ? selectedDocumentIds : null,
        conversation_id: isRealConvId ? activeConversationId : null,
        top_k: 5,
      });

      upsertConversation({
        id: response.conversation_id,
        title: trimmed.length > 65 ? `${trimmed.slice(0, 62)}...` : trimmed,
        created_at: response.created_at,
      });

      const assistantMsg: IMessage = {
        id: response.message_id || `assistant-${Date.now()}`,
        conversation_id: response.conversation_id,
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        created_at: response.created_at,
      };
      addMessage(assistantMsg);

      if (response.sources && response.sources.length > 0) {
        openCitation(response.sources[0], response.sources);
      } else {
        setActiveCitation(null, []);
      }
    } catch (error) {
      const isOfflineNetwork =
        error instanceof ApiClientError && error.isNetworkError;

      if (isOfflineNetwork) {
        // Chế độ xem trước giao diện khi chưa khởi chạy máy chủ Backend
        await new Promise((r) => window.setTimeout(r, 650));
        if (!activeConversationId) {
          upsertConversation({
            id: tempConvId,
            title: trimmed.length > 65 ? `${trimmed.slice(0, 62)}...` : trimmed,
            created_at: new Date().toISOString(),
          });
        }

        const selectedDocsNames = documents
          .filter((d) => selectedDocumentIds.includes(d.id))
          .map((d) => d.filename)
          .join(", ");

        const demoAssistantMsg: IMessage = {
          id: `assistant-${Date.now()}`,
          conversation_id: tempConvId,
          role: "assistant",
          content:
            `Dựa trên tài liệu đang chọn (**${selectedDocsNames || "Tài liệu mẫu"}**), dưới đây là thông tin tra cứu cho câu hỏi của bạn:\n\n` +
            `- **Quy định nghỉ phép năm:** Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm **12 ngày làm việc** hưởng nguyên lương [S1].\n` +
            `- **Chế độ thâm niên:** Cứ đủ **05 năm làm việc liên tục**, số ngày nghỉ hằng năm được tăng thêm **01 ngày phép** [S2].`,
          sources: SAMPLE_CITATIONS,
          created_at: new Date().toISOString(),
        };
        addMessage(demoAssistantMsg);
        openCitation(SAMPLE_CITATIONS[0], SAMPLE_CITATIONS);
      } else {
        // [SP5-05.4] Hiển thị Toast Notification rõ ràng khi Backend trả lỗi (LLM timeout, không có tài liệu hợp lệ...)
        const errMsg =
          error instanceof Error
            ? error.message
            : "Đã xảy ra lỗi khi xử lý câu hỏi trên máy chủ.";
        toast({
          title: "Không thể hoàn tất câu trả lời",
          description: errMsg,
          variant: "danger",
        });
      }
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Danh sách tin nhắn có thanh cuộn tự động ([SP5-03.1]) */}
      <ScrollArea className="flex-1 p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {isLoadingHistory ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Loader2 className="h-7 w-7 animate-spin text-primary" />
              <p className="mt-3 text-sm font-medium text-text-secondary">
                Đang tải lại lịch sử trò chuyện và nguồn trích dẫn...
              </p>
            </div>
          ) : messages.length === 0 && !isSending ? (
            <EmptyChatState
              selectedDocumentsCount={selectedDocumentIds.length}
              onSelectSuggestion={(suggestion) => {
                setQuestionInput(suggestion);
              }}
            />
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                activeCitation={activeCitation}
                onSelectCitation={(citation, allSources) =>
                  openCitation(citation, allSources)
                }
              />
            ))
          )}

          {/* Hiển thị khung xương chờ khi hệ thống đang xử lý ([SP5-03.4]) */}
          {isSending && <ChatTypingSkeleton />}

          {/* Điểm neo tự động cuộn xuống cuối */}
          <div ref={bottomAnchorRef} />
        </div>
      </ScrollArea>

      {/* Ô nhập câu hỏi tự giãn chiều cao ([SP5-03.3]) */}
      <ChatInputBox
        value={questionInput}
        onChange={setQuestionInput}
        onSubmit={handleSendQuestion}
        isSending={isSending || isLoadingHistory}
        selectedDocumentsCount={selectedDocumentIds.length}
      />
    </div>
  );
}

export const MessageList = ChatWindow;
