import * as React from "react";
import {
  Sparkles,
  Server,
  PanelRightClose,
  PanelRightOpen,
  UserCircle2,
  FileCheck2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDocumentsStore } from "@/features/documents/useDocuments";
import { useActiveCitation } from "@/features/chat/useActiveCitation";
import { fetchHealthStatus } from "@/services/api-client";

export function AppHeader() {
  const { selectedDocumentIds, documents } = useDocumentsStore();
  const { isSourcePanelOpen, toggleSourcePanel, activeCitation } =
    useActiveCitation();

  const [backendStatus, setBackendStatus] = React.useState<
    "checking" | "online" | "offline"
  >("checking");

  React.useEffect(() => {
    let mounted = true;
    fetchHealthStatus()
      .then(() => {
        if (mounted) setBackendStatus("online");
      })
      .catch(() => {
        if (mounted) setBackendStatus("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  const processedCount = documents.filter(
    (d) => d.status === "processed"
  ).length;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-default bg-bg-surface px-5">
      {/* Thương hiệu ứng dụng */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white shadow-xs">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-[17px] font-bold leading-tight text-text-primary">
            Intelligent Document Chatbot
          </h1>
          <p className="text-xs text-text-muted">
            Trợ lý Hỏi - Đáp Tài liệu RAG • Trích dẫn xác thực 2 lớp [S1], [S2]
          </p>
        </div>
      </div>

      {/* Trạng thái tài liệu đang chọn, kết nối Backend & nút đóng/mở Panel Nguồn */}
      <div className="flex items-center gap-2.5">
        <Badge variant="default" className="gap-1.5">
          <FileCheck2 className="h-3.5 w-3.5" />
          Đang chọn: {selectedDocumentIds.length}/{processedCount} tài liệu
        </Badge>

        <Badge
          variant={
            backendStatus === "online"
              ? "success"
              : backendStatus === "checking"
              ? "warning"
              : "muted"
          }
        >
          <Server className="h-3.5 w-3.5" />
          {backendStatus === "online"
            ? "Backend API: Sẵn sàng"
            : backendStatus === "checking"
            ? "Đang kết nối API..."
            : "Chế độ Giao diện"}
        </Badge>

        <Button
          variant="outline"
          size="sm"
          onClick={toggleSourcePanel}
          title={
            isSourcePanelOpen
              ? "Thu gọn Panel nguồn trích dẫn"
              : "Mở Panel nguồn trích dẫn"
          }
        >
          {isSourcePanelOpen ? (
            <PanelRightClose className="h-4 w-4 text-primary" />
          ) : (
            <PanelRightOpen className="h-4 w-4 text-text-secondary" />
          )}
          <span className="hidden sm:inline">
            Nguồn trích dẫn
            {activeCitation ? ` [${activeCitation.source_id}]` : ""}
          </span>
        </Button>

        <div className="ml-1 flex items-center gap-1.5 rounded-lg border border-border-default bg-bg-app px-2.5 py-1 text-xs font-medium text-text-secondary">
          <UserCircle2 className="h-4 w-4 text-primary" />
          <span className="hidden md:inline">Tài khoản</span>
        </div>
      </div>
    </header>
  );
}

