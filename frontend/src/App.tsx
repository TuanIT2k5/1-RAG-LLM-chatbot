import * as React from "react";
import {
  FileText,
  Upload,
  MessageSquarePlus,
  Send,
  BookOpenCheck,
  Sparkles,
  CheckSquare,
  Square,
  Server,
  Palette,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/useToast";
import {
  SAMPLE_DOCUMENTS,
  useDocumentsStore,
} from "@/features/documents/useDocuments";
import {
  SAMPLE_CITATIONS,
  useActiveCitation,
} from "@/features/chat/useActiveCitation";
import { useChatSession } from "@/features/chat/useChatSession";
import { fetchHealthStatus } from "@/services/api-client";

export function WorkspacePreview() {
  const { toast } = useToast();
  const { selectedDocumentIds, toggleDocumentSelection } = useDocumentsStore();
  const { activeCitation, setActiveCitation } = useActiveCitation();
  const { messages, addMessage, resetSession } = useChatSession();

  const [questionInput, setQuestionInput] = React.useState("");
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false);
  const [backendStatus, setBackendStatus] = React.useState<
    "checking" | "online" | "offline"
  >("checking");

  React.useEffect(() => {
    fetchHealthStatus()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  const handleSendQuestion = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = questionInput.trim();
    if (!trimmed) return;

    addMessage({
      id: `user-${Date.now()}`,
      conversation_id: "conv-demo-1",
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    });
    setQuestionInput("");

    toast({
      title: "Đã gửi câu hỏi thử nghiệm",
      description:
        "Luồng RAG đầy đủ sẽ được kết nối trực tiếp ở Sprint 4 & Sprint 5.",
      variant: "default",
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${Math.round(bytes / 1024)} KB`;
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-bg-app text-text-primary">
      {/* HEADER */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-default bg-bg-surface px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white shadow-xs">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-[17px] font-bold leading-tight text-text-primary">
              Intelligent Document Chatbot
            </h1>
            <p className="text-xs text-text-muted">
              LLM + Retrieval-Augmented Generation (RAG) • Sprint 1 Workspace
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="default">
            Đang chọn: {selectedDocumentIds.length} tài liệu
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
              ? "FastAPI: Online (8000)"
              : backendStatus === "checking"
              ? "Đang kiểm tra API..."
              : "FastAPI: Chế độ khung UI"}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              toast({
                title: "Hệ thống Design System đã sẵn sàng!",
                description:
                  "Bảng màu Primary #2563EB, Font Inter / Be Vietnam Pro & JetBrains Mono hoạt động chuẩn xác.",
                variant: "success",
              })
            }
          >
            <Palette className="h-4 w-4" />
            Kiểm tra Toast UI
          </Button>
        </div>
      </header>

      {/* BỐ CỤC 3 CỘT CHUẨN MODERN SAAS (280px | Flex-1 | 360px) */}
      <div className="flex flex-1 overflow-hidden">
        {/* CỘT 1: SIDEBAR TRÁI (280px) */}
        <aside className="flex w-[280px] shrink-0 flex-col border-r border-border-default bg-bg-sidebar p-4">
          <Button
            className="w-full justify-start"
            onClick={() => {
              resetSession();
              toast({
                title: "Đã tạo cuộc trò chuyện mới",
                description: "Sẵn sàng đặt câu hỏi trên các tài liệu đã chọn.",
              });
            }}
          >
            <MessageSquarePlus className="h-4 w-4" />
            Cuộc trò chuyện mới
          </Button>

          <div className="mt-6 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
              Tài liệu của bạn ({SAMPLE_DOCUMENTS.length})
            </span>
            <button
              type="button"
              onClick={() => setUploadModalOpen(true)}
              className="text-xs font-medium text-primary hover:text-primary-hover"
            >
              + Tải lên
            </button>
          </div>

          <ScrollArea className="mt-2.5 flex-1 pr-1">
            <div className="space-y-2">
              {SAMPLE_DOCUMENTS.map((doc) => {
                const isSelected = selectedDocumentIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => toggleDocumentSelection(doc.id)}
                    className={`cursor-pointer rounded-xl border p-3 transition-all ${
                      isSelected
                        ? "border-primary/40 bg-primary-light shadow-2xs"
                        : "border-border-default bg-bg-surface hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 text-primary">
                        {isSelected ? (
                          <CheckSquare className="h-4 w-4" />
                        ) : (
                          <Square className="h-4 w-4 text-text-muted" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-text-primary">
                          {doc.filename}
                        </p>
                        <div className="mt-1.5 flex items-center justify-between">
                          <span className="text-xs text-text-muted">
                            {formatFileSize(doc.file_size)}
                          </span>
                          <Badge
                            variant={
                              doc.status === "processed"
                                ? "success"
                                : doc.status === "processing"
                                ? "warning"
                                : "danger"
                            }
                          >
                            {doc.status === "processed"
                              ? "Sẵn sàng"
                              : doc.status === "processing"
                              ? "Đang xử lý"
                              : "Lỗi"}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>

          <Button
            variant="outline"
            className="mt-3 w-full"
            onClick={() => setUploadModalOpen(true)}
          >
            <Upload className="h-4 w-4" />
            Tải tài liệu mới (PDF/DOCX)
          </Button>
        </aside>

        {/* CỘT 2: KHU VỰC HỘI THOẠI TRUNG TÂM (Flex-1) */}
        <main className="flex flex-1 flex-col bg-bg-surface">
          <ScrollArea className="flex-1 p-6">
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-[1.65] ${
                      msg.role === "user"
                        ? "bg-primary text-white shadow-xs"
                        : "border border-border-default bg-bg-app text-text-primary"
                    }`}
                  >
                    <p className="whitespace-pre-line">{msg.content}</p>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3.5 border-t border-border-default pt-3">
                        <p className="mb-2 text-xs font-semibold text-text-muted">
                          Nguồn tham khảo xác thực (Nhấn để đối chiếu):
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {msg.sources.map((src) => (
                            <Badge
                              key={src.source_id}
                              variant="citation"
                              onClick={() => setActiveCitation(src)}
                            >
                              [{src.source_id}] {src.filename}
                              {src.page_number ? ` • Trang ${src.page_number}` : ""}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* KHUNG NHẬP CÂU HỎI */}
          <div className="border-t border-border-default bg-bg-surface p-4">
            <form
              onSubmit={handleSendQuestion}
              className="mx-auto flex max-w-3xl items-center gap-2.5"
            >
              <Input
                value={questionInput}
                onChange={(e) => setQuestionInput(e.target.value)}
                placeholder="Nhập câu hỏi về các tài liệu đã chọn..."
                className="flex-1"
              />
              <Button type="submit">
                <Send className="h-4 w-4" />
                Gửi câu hỏi
              </Button>
            </form>
          </div>
        </main>

        {/* CỘT 3: PANEL CHI TIẾT NGUỒN TRÍCH DẪN PHẢI (360px) */}
        <aside className="flex w-[360px] shrink-0 flex-col border-l border-border-default bg-bg-sidebar p-4">
          <div className="flex items-center gap-2 pb-3 border-b border-border-default">
            <BookOpenCheck className="h-4 w-4 text-primary" />
            <h2 className="text-[15px] font-semibold text-text-primary">
              Chi tiết nguồn trích dẫn
            </h2>
          </div>

          <ScrollArea className="mt-4 flex-1">
            {activeCitation ? (
              <div className="space-y-4">
                <div className="rounded-xl border border-primary/30 bg-bg-surface p-4 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="rounded-md bg-primary px-2 py-0.5 font-mono text-xs font-semibold text-white">
                      [{activeCitation.source_id}]
                    </span>
                    {activeCitation.score && (
                      <span className="font-mono text-xs text-text-muted">
                        Cosine: {(activeCitation.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div className="mt-3 flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-primary" />
                    <p className="truncate text-sm font-semibold text-text-primary">
                      {activeCitation.filename}
                    </p>
                  </div>

                  <p className="mt-1 text-xs font-medium text-text-muted">
                    {activeCitation.page_number
                      ? `Trang ${activeCitation.page_number}`
                      : "Tài liệu DOCX"}{" "}
                    • Đoạn Chunk #{activeCitation.chunk_index ?? 0}
                  </p>

                  <div className="mt-3 rounded-lg border border-border-default bg-bg-app p-3 text-sm leading-relaxed text-text-secondary italic">
                    &ldquo;{activeCitation.excerpt}&rdquo;
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Tất cả nguồn trong câu trả lời
                  </p>
                  <div className="space-y-2">
                    {SAMPLE_CITATIONS.map((item) => (
                      <button
                        key={item.source_id}
                        type="button"
                        onClick={() => setActiveCitation(item)}
                        className={`w-full rounded-lg border p-2.5 text-left text-xs transition-colors ${
                          activeCitation.source_id === item.source_id
                            ? "border-primary bg-primary-light text-primary font-medium"
                            : "border-border-default bg-bg-surface text-text-secondary hover:bg-slate-50"
                        }`}
                      >
                        <span className="font-mono font-semibold">
                          [{item.source_id}]
                        </span>{" "}
                        {item.filename}{" "}
                        {item.page_number ? `(Trang ${item.page_number})` : ""}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-text-muted">
                Nhấn vào nhãn [S1], [S2] trong câu trả lời để đối chiếu văn bản
                gốc.
              </p>
            )}
          </ScrollArea>
        </aside>
      </div>

      {/* DIALOG TẢI TÀI LIỆU MỚI (SHADCN/UI DIALOG DEMO) */}
      <Dialog open={uploadModalOpen} onOpenChange={setUploadModalOpen}>
        <DialogHeader>
          <DialogTitle>Tải lên tài liệu mới (PDF / DOCX)</DialogTitle>
          <DialogDescription>
            Hỗ trợ tệp văn bản .pdf và .docx có dung lượng tối đa 20MB/tệp.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-primary/40 bg-primary-light/50 p-8 text-center">
          <Upload className="h-8 w-8 text-primary mb-2" />
          <p className="text-sm font-medium text-text-primary">
            Kéo thả tệp PDF hoặc DOCX vào đây
          </p>
          <p className="mt-1 text-xs text-text-muted">
            Tự động chuẩn hóa Unicode NFC, chia Chunk 400 tokens & lập chỉ mục
            ChromaDB
          </p>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => setUploadModalOpen(false)}>
            Đóng
          </Button>
          <Button
            onClick={() => {
              setUploadModalOpen(false);
              toast({
                title: "Đã sẵn sàng kết nối API Upload",
                description:
                  "Chức năng POST /api/documents/upload sẽ hoàn thiện ở Sprint 2 & Sprint 4.",
                variant: "success",
              });
            }}
          >
            Chọn tệp từ máy tính
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}

export default function App() {
  return <WorkspacePreview />;
}

