import * as React from "react";
import {
  FileText,
  X,
  MessageSquare,
  Layers,
  BookOpenCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AppHeader } from "@/components/layout/AppHeader";
import { LeftSidebar } from "@/components/layout/LeftSidebar";
import { RightSourcePanel } from "@/components/layout/RightSourcePanel";
import { useDocumentsStore } from "@/features/documents/useDocuments";
import { useChatSession } from "@/features/chat/useChatSession";
import { useActiveCitation } from "@/features/chat/useActiveCitation";

interface WorkspaceLayoutProps {
  children: React.ReactNode;
}

export function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  const {
    documents,
    selectedDocumentIds,
    toggleDocumentSelection,
    selectAllProcessedDocuments,
  } = useDocumentsStore();

  const { conversations, activeConversationId } = useChatSession();
  const { isSourcePanelOpen, toggleSourcePanel, activeCitation } =
    useActiveCitation();

  const selectedDocuments = documents.filter((doc) =>
    selectedDocumentIds.includes(doc.id)
  );
  const processedDocuments = documents.filter(
    (doc) => doc.status === "processed"
  );

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg-app text-text-primary">
      {/* 1. HEADER TRÊN CÙNG ([SP5-01.1]) */}
      <AppHeader />

      {/* 2. BỐ CỤC 3 CỘT CHUẨN MODERN SAAS DASHBOARD (280px | Flex-1 | 360px) */}
      <div className="flex flex-1 overflow-hidden">
        {/* CỘT 1: SIDEBAR BÊN TRÁI (280px, nền #F1F5F9) ([SP5-01.1]) */}
        <LeftSidebar />

        {/* CỘT 2: KHUNG HỘI THOẠI CHÍNH Ở GIỮA (flex-1, nền #FFFFFF) ([SP5-01.2]) */}
        <main className="flex min-w-0 flex-1 flex-col bg-[#FFFFFF]">
          {/* Thanh tiêu đề ngữ cảnh hiển thị phiên hội thoại và các tài liệu đang được chọn ([SP5-01.2]) */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-default bg-bg-surface px-5 py-2.5">
            <div className="flex min-w-0 items-center gap-2">
              <MessageSquare className="h-4 w-4 shrink-0 text-primary" />
              <h2 className="truncate text-sm font-semibold text-text-primary">
                {activeConversation
                  ? activeConversation.title
                  : "Cuộc trò chuyện mới"}
              </h2>
            </div>

            {/* Danh sách các tài liệu đang được chọn làm phạm vi tra cứu RAG */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="flex items-center gap-1 text-xs font-medium text-text-muted">
                <Layers className="h-3.5 w-3.5 text-primary" />
                Phạm vi tra cứu:
              </span>

              {selectedDocuments.length > 0 ? (
                selectedDocuments.map((doc) => (
                  <span
                    key={doc.id}
                    className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary-light px-2 py-0.5 text-xs font-medium text-primary"
                  >
                    <FileText className="h-3 w-3 shrink-0" />
                    <span className="max-w-[160px] truncate">{doc.filename}</span>
                    <button
                      type="button"
                      title={`Bỏ chọn ${doc.filename}`}
                      onClick={() => toggleDocumentSelection(doc.id)}
                      className="rounded-xs p-0.5 text-primary/70 hover:bg-primary/10 hover:text-primary"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))
              ) : (
                <div className="flex items-center gap-2">
                  <Badge variant="warning">
                    Chưa chọn tài liệu ({processedDocuments.length} sẵn sàng)
                  </Badge>
                  {processedDocuments.length > 0 && (
                    <button
                      type="button"
                      onClick={selectAllProcessedDocuments}
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      Chọn tất cả
                    </button>
                  )}
                </div>
              )}

              {!isSourcePanelOpen && activeCitation && (
                <button
                  type="button"
                  onClick={toggleSourcePanel}
                  className="ml-1 inline-flex items-center gap-1 rounded-md border border-border-default bg-bg-app px-2 py-0.5 text-xs font-medium text-text-secondary hover:border-primary/40 hover:text-primary"
                >
                  <BookOpenCheck className="h-3.5 w-3.5 text-primary" />
                  Mở nguồn [{activeCitation.source_id}]
                </button>
              )}
            </div>
          </div>

          {/* Nội dung khung Chat & Ô nhập câu hỏi */}
          {children}
        </main>

        {/* CỘT 3: PANEL NGUỒN TRÍCH DẪN BÊN PHẢI (360px, đóng/mở mượt mà) ([SP5-01.3]) */}
        <RightSourcePanel />
      </div>
    </div>
  );
}

