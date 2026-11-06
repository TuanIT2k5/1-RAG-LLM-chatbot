import * as React from "react";
import { FileText, AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { DocumentCard } from "@/components/documents/DocumentCard";
import { useToast } from "@/hooks/useToast";
import { useDocumentsStore } from "@/features/documents/useDocuments";
import { fetchDocuments, deleteDocumentById } from "@/services/document-api";
import type { IDocument } from "@/types";

const POLLING_INTERVAL_MS = 2500;

export function DocumentList() {
  const { toast } = useToast();
  const {
    documents,
    selectedDocumentIds,
    toggleDocumentSelection,
    setDocuments,
    removeDocument,
    setIsLoadingDocuments,
  } = useDocumentsStore();

  const [docPendingDelete, setDocPendingDelete] =
    React.useState<IDocument | null>(null);
  const [isDeleting, setIsDeleting] = React.useState(false);

  // Tải danh sách tài liệu từ Backend khi khởi động
  const syncDocumentsFromServer = React.useCallback(async () => {
    try {
      const res = await fetchDocuments();
      if (Array.isArray(res.items)) {
        setDocuments(res.items);
      }
    } catch {
      // Giữ danh sách mẫu nếu đang chạy giao diện độc lập chưa bật Backend
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [setDocuments, setIsLoadingDocuments]);

  React.useEffect(() => {
    setIsLoadingDocuments(true);
    syncDocumentsFromServer();
  }, [syncDocumentsFromServer, setIsLoadingDocuments]);

  // [SP5-02.2] Tự động Polling/Refetch định kỳ khi có tài liệu đang ở trạng thái 'processing'
  const hasProcessingDocs = documents.some(
    (doc) => doc.status === "processing" && !doc.id.startsWith("temp-")
  );

  React.useEffect(() => {
    if (!hasProcessingDocs) return;

    const timer = window.setInterval(() => {
      syncDocumentsFromServer();
    }, POLLING_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [hasProcessingDocs, syncDocumentsFromServer]);

  const handleSelectToggle = (docId: string) => {
    const target = documents.find((d) => d.id === docId);
    if (!target) return;

    if (target.status !== "processed") {
      toast({
        title: "Tài liệu chưa sẵn sàng",
        description:
          target.status === "processing"
            ? "Tài liệu đang được lập chỉ mục vector. Vui lòng đợi hoàn tất."
            : "Tài liệu bị lỗi xử lý nên không thể chọn tra cứu.",
        variant: "warning",
      });
      return;
    }

    toggleDocumentSelection(docId);
  };

  // [SP5-02.4] Xác nhận và thực thi xóa đồng bộ tài liệu
  const handleConfirmDelete = async () => {
    if (!docPendingDelete || isDeleting) return;
    const targetDoc = docPendingDelete;
    setIsDeleting(true);

    try {
      const isDemoDoc =
        targetDoc.id.startsWith("doc-demo-") ||
        targetDoc.id.startsWith("temp-");

      if (!isDemoDoc) {
        await deleteDocumentById(targetDoc.id);
      }

      removeDocument(targetDoc.id);
      toast({
        title: "Đã xóa tài liệu thành công",
        description: `Đã xóa đồng bộ "${targetDoc.filename}" khỏi ChromaDB, ổ cứng và CSDL.`,
        variant: "success",
      });
      setDocPendingDelete(null);
    } catch (error) {
      const msg =
        error instanceof Error
          ? error.message
          : "Không thể xóa tài liệu vào lúc này.";
      toast({
        title: "Lỗi khi xóa tài liệu",
        description: msg,
        variant: "danger",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      {documents.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border-default bg-bg-surface p-4 text-center">
          <FileText className="mx-auto h-6 w-6 text-text-muted" />
          <p className="mt-1.5 text-xs text-text-muted">
            Chưa có tài liệu nào. Hãy nhấn &ldquo;+ Tải tài liệu mới&rdquo; để
            thêm tệp PDF hoặc DOCX.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              isSelected={selectedDocumentIds.includes(doc.id)}
              onToggleSelect={handleSelectToggle}
              onRequestDelete={(item) => setDocPendingDelete(item)}
            />
          ))}
        </div>
      )}

      {/* Hộp thoại xác nhận xóa tài liệu (Confirm Dialog - [SP5-02.4]) */}
      <Dialog
        open={docPendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !isDeleting) {
            setDocPendingDelete(null);
          }
        }}
      >
        <DialogHeader>
          <div className="flex items-center gap-2.5 text-[#DC2626]">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <DialogTitle>Xác nhận xóa tài liệu</DialogTitle>
          </div>
          <DialogDescription>
            Bạn có chắc chắn muốn xóa tài liệu{" "}
            <span className="font-semibold text-text-primary">
              &ldquo;{docPendingDelete?.filename}&rdquo;
            </span>{" "}
            không?
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-xl border border-red-200 bg-red-50/70 p-3 text-xs leading-relaxed text-text-secondary">
          Hành động này sẽ <strong>xóa đồng bộ vĩnh viễn ở cả 3 nơi</strong>:
          <ul className="mt-1.5 list-inside list-disc space-y-1">
            <li>Toàn bộ vector Chunks của tài liệu trong ChromaDB</li>
            <li>Tệp vật lý gốc trong thư mục lưu trữ máy chủ</li>
            <li>Bản ghi metadata trong cơ sở dữ liệu PostgreSQL</li>
          </ul>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="secondary"
            disabled={isDeleting}
            onClick={() => setDocPendingDelete(null)}
          >
            Hủy bỏ
          </Button>
          <Button
            type="button"
            variant="danger"
            disabled={isDeleting}
            onClick={handleConfirmDelete}
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang xóa...
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4" />
                Xóa vĩnh viễn
              </>
            )}
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}
