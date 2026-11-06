import * as React from "react";
import {
  MessageSquarePlus,
  Upload,
  MessageSquare,
  Trash2,
  FolderOpen,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DocumentList } from "@/components/documents/DocumentList";
import { useToast } from "@/hooks/useToast";
import { useDocumentsStore } from "@/features/documents/useDocuments";
import { useChatSession } from "@/features/chat/useChatSession";
import { useActiveCitation } from "@/features/chat/useActiveCitation";
import {
  fetchConversations,
  fetchConversationMessages,
  deleteConversationById,
} from "@/services/chat-api";
import type { IConversation } from "@/types";

export function LeftSidebar() {
  const { toast } = useToast();
  const {
    documents,
    selectedDocumentIds,
    selectAllProcessedDocuments,
    clearDocumentSelection,
    setUploadModalOpen,
  } = useDocumentsStore();

  const {
    conversations,
    activeConversationId,
    isLoadingHistory,
    setConversations,
    selectConversation,
    startNewConversation,
    removeConversation,
    setIsLoadingHistory,
  } = useChatSession();

  const { setActiveCitation } = useActiveCitation();
  const [deletingConvId, setDeletingConvId] = React.useState<string | null>(
    null
  );

  // [SP5-05.3] Đồng bộ danh sách lịch sử hội thoại từ Backend khi khởi động
  React.useEffect(() => {
    let isMounted = true;

    async function syncConversations() {
      try {
        const res = await fetchConversations(0, 50);
        if (!isMounted) return;

        if (Array.isArray(res.items) && res.items.length > 0) {
          setConversations(res.items);
          // Tự động tải tin nhắn và trích dẫn của phiên hội thoại mới nhất
          const latestConv = res.items[0];
          setIsLoadingHistory(true);
          try {
            const history = await fetchConversationMessages(latestConv.id);
            if (!isMounted) return;
            selectConversation(latestConv.id, history.messages);

            const lastMsgWithSources = [...history.messages]
              .reverse()
              .find((m) => m.role === "assistant" && m.sources && m.sources.length > 0);
            if (lastMsgWithSources && lastMsgWithSources.sources) {
              setActiveCitation(
                lastMsgWithSources.sources[0],
                lastMsgWithSources.sources
              );
            } else {
              setActiveCitation(null, []);
            }
          } finally {
            if (isMounted) setIsLoadingHistory(false);
          }
        }
      } catch {
        // Nếu đang chạy chế độ khung giao diện độc lập chưa bật Backend, giữ nguyên dữ liệu mẫu
      }
    }

    void syncConversations();
    return () => {
      isMounted = false;
    };
  }, [
    setConversations,
    selectConversation,
    setActiveCitation,
    setIsLoadingHistory,
  ]);

  const processedDocs = documents.filter((d) => d.status === "processed");
  const allProcessedSelected =
    processedDocs.length > 0 &&
    processedDocs.every((d) => selectedDocumentIds.includes(d.id));

  const handleNewConversation = () => {
    startNewConversation();
    setActiveCitation(null, []);
    toast({
      title: "Đã tạo cuộc trò chuyện mới",
      description:
        "Hãy nhập câu hỏi bên dưới để tra cứu trên các tài liệu đã chọn.",
    });
  };

  // [SP5-05.3] Nhấn chọn phiên chat cũ để tải lại toàn bộ tin nhắn và trích dẫn trước đó
  const handleSelectConversation = async (conv: IConversation) => {
    if (conv.id === activeConversationId && !isLoadingHistory) return;

    const isDemoConv =
      conv.id.startsWith("conv-demo-") || conv.id.startsWith("conv-");

    if (isDemoConv) {
      selectConversation(conv.id);
      const currentMessages = useChatSession.getState().messages;
      const lastWithSources = [...currentMessages]
        .reverse()
        .find((m) => m.role === "assistant" && m.sources && m.sources.length > 0);
      if (lastWithSources?.sources) {
        setActiveCitation(lastWithSources.sources[0], lastWithSources.sources);
      } else {
        setActiveCitation(null, []);
      }
      return;
    }

    setIsLoadingHistory(true);
    try {
      const history = await fetchConversationMessages(conv.id);
      selectConversation(conv.id, history.messages);

      const lastWithSources = [...history.messages]
        .reverse()
        .find((m) => m.role === "assistant" && m.sources && m.sources.length > 0);
      if (lastWithSources?.sources) {
        setActiveCitation(lastWithSources.sources[0], lastWithSources.sources);
      } else {
        setActiveCitation(null, []);
      }
    } catch (error) {
      const msg =
        error instanceof Error
          ? error.message
          : "Không thể tải lại lịch sử trò chuyện từ máy chủ.";
      toast({
        title: "Lỗi tải lịch sử hội thoại",
        description: msg,
        variant: "danger",
      });
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // [SP5-05.3 & SP5-05.4] Xóa phiên hội thoại trên Backend và hiển thị Toast thông báo
  const handleDeleteConversation = async (
    e: React.MouseEvent,
    conv: IConversation
  ) => {
    e.stopPropagation();
    if (deletingConvId) return;

    setDeletingConvId(conv.id);
    try {
      const isDemoConv =
        conv.id.startsWith("conv-demo-") || conv.id.startsWith("conv-");
      if (!isDemoConv) {
        await deleteConversationById(conv.id);
      }

      if (activeConversationId === conv.id) {
        setActiveCitation(null, []);
      }
      removeConversation(conv.id);

      toast({
        title: "Đã xóa phiên hội thoại",
        description: `Đã xóa "${conv.title}" khỏi lịch sử trò chuyện.`,
        variant: "success",
      });
    } catch (error) {
      const msg =
        error instanceof Error
          ? error.message
          : "Không thể xóa phiên hội thoại vào lúc này.";
      toast({
        title: "Xóa phiên hội thoại thất bại",
        description: msg,
        variant: "danger",
      });
    } finally {
      setDeletingConvId(null);
    }
  };

  return (
    <aside
      aria-label="Sidebar quản lý tài liệu và lịch sử hội thoại"
      className="flex w-[280px] shrink-0 flex-col border-r border-border-default bg-[#F1F5F9] p-4"
    >
      {/* Nút tạo cuộc trò chuyện mới ([SP5-01.1]) */}
      <Button
        className="w-full justify-start gap-2 shadow-xs"
        onClick={handleNewConversation}
      >
        <MessageSquarePlus className="h-4 w-4" />
        Cuộc trò chuyện mới
      </Button>

      {/* PHẦN 1: DANH SÁCH TÀI LIỆU CỦA BẠN ([SP5-02.2 -> SP5-02.4]) */}
      <div className="mt-5 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <FolderOpen className="h-3.5 w-3.5 text-text-muted" />
          <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
            Tài liệu của bạn ({documents.length})
          </span>
        </div>

        {processedDocs.length > 0 && (
          <button
            type="button"
            onClick={() =>
              allProcessedSelected
                ? clearDocumentSelection()
                : selectAllProcessedDocuments()
            }
            className="text-xs font-medium text-primary hover:text-primary-hover"
          >
            {allProcessedSelected ? "Bỏ chọn" : "Chọn tất cả"}
          </button>
        )}
      </div>

      <ScrollArea className="mt-2 max-h-[46%] flex-1 pr-1">
        <DocumentList />
      </ScrollArea>

      <Button
        variant="outline"
        size="sm"
        className="mt-2.5 w-full bg-bg-surface hover:bg-slate-50"
        onClick={() => setUploadModalOpen(true)}
      >
        <Upload className="h-4 w-4 text-primary" />
        + Tải tài liệu mới
      </Button>

      {/* PHẦN 2: DANH SÁCH LỊCH SỬ HỘI THOẠI ([SP5-01.1 & SP5-05.3]) */}
      <div className="mt-5 border-t border-border-default pt-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
            Lịch sử hội thoại ({conversations.length})
          </span>
          {isLoadingHistory && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          )}
        </div>
      </div>

      <ScrollArea className="mt-2 flex-1 pr-1">
        {conversations.length === 0 ? (
          <p className="px-1 py-3 text-xs text-text-muted">
            Chưa có lịch sử trò chuyện nào được lưu.
          </p>
        ) : (
          <div className="space-y-1.5">
            {conversations.map((conv) => {
              const isActive = activeConversationId === conv.id;
              const isDeletingThis = deletingConvId === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => void handleSelectConversation(conv)}
                  className={`group flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-xs transition-colors ${
                    isActive
                      ? "border-primary/40 bg-primary-light font-semibold text-primary"
                      : "border-transparent bg-transparent text-text-secondary hover:border-border-default hover:bg-bg-surface"
                  }`}
                >
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <MessageSquare
                      className={`h-3.5 w-3.5 shrink-0 ${
                        isActive ? "text-primary" : "text-text-muted"
                      }`}
                    />
                    <span title={conv.title} className="truncate">
                      {conv.title}
                    </span>
                  </div>

                  <button
                    type="button"
                    title="Xóa cuộc trò chuyện"
                    disabled={isDeletingThis}
                    onClick={(e) => void handleDeleteConversation(e, conv)}
                    className="text-text-muted opacity-0 transition-opacity hover:text-status-danger group-hover:opacity-100 disabled:opacity-50"
                  >
                    {isDeletingThis ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}
