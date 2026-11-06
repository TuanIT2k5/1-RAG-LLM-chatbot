import {
  FileText,
  FileType2,
  CheckSquare,
  Square,
  Trash2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import type { IDocument } from "@/types";

export function formatDocumentSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export interface DocumentCardProps {
  document: IDocument;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onRequestDelete: (document: IDocument) => void;
}

/**
 * [SP5-02.3 & SP5-02.4] Thẻ hiển thị từng tài liệu (DocumentCard / DocumentItem):
 * - Biểu tượng phân biệt PDF / DOCX, tên tệp, dung lượng và số đoạn Chunk.
 * - Nhãn màu trạng thái chuẩn: #16A34A (Sẵn sàng), #D97706 (Đang xử lý), #DC2626 (Lỗi).
 * - Tích hợp Checkbox chọn lọc phạm vi hỏi đáp và nút Xóa mở hộp thoại xác nhận.
 */
export function DocumentCard({
  document,
  isSelected,
  onToggleSelect,
  onRequestDelete,
}: DocumentCardProps) {
  const isSelectable = document.status === "processed";
  const isPdf = document.file_type === "pdf" || document.filename.toLowerCase().endsWith(".pdf");

  const renderStatusBadge = () => {
    if (document.status === "processed") {
      return (
        <span
          style={{
            backgroundColor: "#DCFCE7",
            color: "#16A34A",
            borderColor: "#BBF7D0",
          }}
          className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold"
        >
          <span
            style={{ backgroundColor: "#16A34A" }}
            className="h-1.5 w-1.5 rounded-full"
          />
          Sẵn sàng
        </span>
      );
    }

    if (document.status === "processing") {
      return (
        <span
          style={{
            backgroundColor: "#FEF3C7",
            color: "#D97706",
            borderColor: "#FDE68A",
          }}
          className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold"
        >
          <Loader2 className="h-3 w-3 animate-spin" />
          Đang xử lý
        </span>
      );
    }

    return (
      <span
        style={{
          backgroundColor: "#FEE2E2",
          color: "#DC2626",
          borderColor: "#FECACA",
        }}
        title={document.error_message || "Xử lý tài liệu thất bại"}
        className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold"
      >
        <AlertCircle className="h-3 w-3" />
        Lỗi
      </span>
    );
  };

  return (
    <div
      onClick={() => onToggleSelect(document.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onToggleSelect(document.id);
        }
      }}
      className={`group relative rounded-xl border p-2.5 transition-all ${
        !isSelectable
          ? "cursor-default border-border-default bg-bg-surface/80"
          : isSelected
          ? "cursor-pointer border-primary/50 bg-primary-light shadow-2xs"
          : "cursor-pointer border-border-default bg-bg-surface hover:border-slate-300"
      }`}
    >
      <div className="flex items-start gap-2.5">
        {/* Ô đánh dấu Checkbox chọn tài liệu ([SP5-02.4]) */}
        <button
          type="button"
          aria-label={`Chọn tài liệu ${document.filename}`}
          disabled={!isSelectable}
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect(document.id);
          }}
          className={`mt-0.5 shrink-0 transition-colors ${
            !isSelectable
              ? "cursor-not-allowed text-slate-300"
              : isSelected
              ? "text-primary"
              : "text-text-muted hover:text-primary"
          }`}
        >
          {isSelected ? (
            <CheckSquare className="h-4 w-4" />
          ) : (
            <Square className="h-4 w-4" />
          )}
        </button>

        {/* Biểu tượng loại tệp PDF / DOCX ([SP5-02.3]) */}
        <div
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-xs font-bold ${
            isPdf
              ? "border-red-200 bg-red-50 text-red-600"
              : "border-blue-200 bg-blue-50 text-blue-600"
          }`}
          title={isPdf ? "Tài liệu PDF" : "Tài liệu Word DOCX"}
        >
          {isPdf ? (
            <FileText className="h-4 w-4" />
          ) : (
            <FileType2 className="h-4 w-4" />
          )}
        </div>

        {/* Thông tin tên tệp, dung lượng và trạng thái */}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-1">
            <p
              title={document.filename}
              className="truncate text-sm font-medium text-text-primary"
            >
              {document.filename}
            </p>

            {/* Nút xóa tài liệu mở hộp thoại xác nhận ([SP5-02.4]) */}
            <button
              type="button"
              title={`Xóa tài liệu ${document.filename}`}
              onClick={(e) => {
                e.stopPropagation();
                onRequestDelete(document);
              }}
              className="shrink-0 rounded-md p-1 text-text-muted opacity-0 transition-opacity hover:bg-red-50 hover:text-[#DC2626] group-hover:opacity-100 focus:opacity-100"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="mt-1.5 flex items-center justify-between gap-1">
            <span className="text-xs text-text-muted">
              <span className="font-mono uppercase">{isPdf ? "PDF" : "DOCX"}</span>
              {" • "}
              {formatDocumentSize(document.file_size)}
              {document.chunk_count > 0 ? ` • ${document.chunk_count} đoạn` : ""}
            </span>

            {renderStatusBadge()}
          </div>

          {document.status === "failed" && document.error_message && (
            <p className="mt-1 truncate text-[11px] text-[#DC2626]">
              {document.error_message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export const DocumentItem = DocumentCard;

