import * as React from "react";
import {
  FileText,
  Quote,
  CheckCircle2,
  ExternalLink,
  Copy,
  Check,
  Eye,
  X,
  Highlighter,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getDocumentFileUrl } from "@/services/document-api";
import type { ICitationSource } from "@/types";

interface SourceDetailViewerProps {
  citation: ICitationSource;
}

/**
 * [SP5-04.3 & SP5-04.4] Khung chi tiết nguồn trích dẫn & Đối chiếu trang PDF gốc.
 * - [SP5-04.3] Hiển thị đầy đủ đoạn văn bản gốc (excerpt) được tô sáng (highlight) nổi bật,
 *   kèm nút sao chép nhanh đoạn trích.
 * - [SP5-04.4] Tích hợp nút "[Xem trang X bản PDF]" mở trình xem nhanh trang PDF tương ứng
 *   (hoặc mở tab mới #page=X) để người dùng kiểm chứng trực tiếp trên tài liệu gốc.
 */
export function SourceDetailViewer({ citation }: SourceDetailViewerProps) {
  const [copied, setCopied] = React.useState(false);
  const [isPdfPreviewOpen, setIsPdfPreviewOpen] = React.useState(false);

  const isPdf =
    citation.filename.toLowerCase().endsWith(".pdf") ||
    citation.page_number !== null;
  const pageNumber = citation.page_number ?? 1;
  const isDemoDoc = citation.document_id.startsWith("doc-demo");

  // URL tới endpoint phục vụ tệp gốc của Backend kèm neo #page=X chuẩn trình xem PDF
  const pdfFileUrl = getDocumentFileUrl(citation.document_id, pageNumber);

  const handleCopyExcerpt = async () => {
    try {
      await navigator.clipboard.writeText(citation.excerpt);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Fallback im lặng nếu trình duyệt chặn clipboard
    }
  };

  return (
    <>
      <div className="rounded-xl border border-primary/30 bg-bg-surface p-4 shadow-2xs">
        {/* Hàng nhãn [S1] + Trạng thái xác thực 2 lớp + Độ khớp */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-primary px-2 py-0.5 font-mono text-xs font-semibold text-white">
              [{citation.source_id}]
            </span>
            <Badge variant="success" className="gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Đã xác thực 2 lớp
            </Badge>
          </div>

          {typeof citation.score === "number" && (
            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs font-semibold text-text-secondary">
              Độ khớp: {(citation.score * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {/* Thông tin tệp nguồn + Số trang PDF / Thứ tự đoạn DOCX */}
        <div className="mt-3 flex items-start gap-2.5 rounded-lg bg-slate-50 p-2.5 border border-border-default">
          <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <div className="min-w-0 flex-1">
            <p
              title={citation.filename}
              className="break-words text-sm font-semibold text-text-primary"
            >
              {citation.filename}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 font-mono text-xs font-medium text-text-muted">
              <span className="rounded bg-primary-light px-1.5 py-0.5 font-semibold text-primary">
                {citation.page_number
                  ? `Trang ${citation.page_number}`
                  : "Tài liệu DOCX"}
              </span>
              <span>•</span>
              <span>Đoạn (Chunk) #{citation.chunk_index ?? 0}</span>
            </div>
          </div>
        </div>

        {/* [SP5-04.3] Đoạn văn bản gốc (Excerpt) được tô sáng (Highlight) */}
        <div className="mt-3.5">
          <div className="mb-1.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-text-secondary">
              <Highlighter className="h-3.5 w-3.5 text-amber-600" />
              <span>Đoạn văn bản gốc (Được tô sáng):</span>
            </div>

            <button
              type="button"
              onClick={() => void handleCopyExcerpt()}
              title="Sao chép đoạn trích gốc"
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium text-text-muted transition-colors hover:bg-slate-100 hover:text-text-primary"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-emerald-600" />
                  <span className="text-emerald-600">Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Sao chép</span>
                </>
              )}
            </button>
          </div>

          <div className="relative rounded-xl border border-amber-300/90 bg-amber-50/75 p-3.5 shadow-2xs">
            <Quote className="mb-1 h-4 w-4 text-amber-600/80" />
            <mark className="block rounded bg-amber-200/65 px-1.5 py-1 text-sm leading-relaxed text-slate-900">
              &ldquo;{citation.excerpt}&rdquo;
            </mark>
          </div>
        </div>

        {/* [SP5-04.4] Nút mở xem nhanh trang PDF tương ứng để kiểm chứng trực tiếp */}
        <div className="mt-3.5 flex flex-wrap items-center gap-2 pt-1">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setIsPdfPreviewOpen(true)}
            className="w-full justify-center gap-1.5 font-semibold"
          >
            <Eye className="h-3.5 w-3.5" />
            {isPdf
              ? `Xem trang ${pageNumber} bản PDF`
              : `Xem nhanh tài liệu gốc (Đoạn #${citation.chunk_index ?? 0})`}
          </Button>
        </div>
      </div>

      {/* [SP5-04.4] Hộp thoại (Modal) Xem nhanh Trang PDF gốc */}
      {isPdfPreviewOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Xem trước tài liệu ${citation.filename} - Trang ${pageNumber}`}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs"
        >
          <div className="flex h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-border-default bg-bg-surface shadow-xl">
            {/* Thanh tiêu đề Modal */}
            <div className="flex items-center justify-between border-b border-border-default bg-slate-50 px-5 py-3.5">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className="rounded-md bg-primary px-2 py-0.5 font-mono text-xs font-semibold text-white">
                  [{citation.source_id}]
                </span>
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-text-primary">
                    {citation.filename}
                  </h3>
                  <p className="font-mono text-xs text-text-muted">
                    {citation.page_number
                      ? `Đang đối chiếu Trang ${citation.page_number}`
                      : `Đoạn (Chunk) #${citation.chunk_index ?? 0}`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {!isDemoDoc && (
                  <a
                    href={pdfFileUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border-default bg-white px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-slate-100"
                  >
                    <ExternalLink className="h-3.5 w-3.5 text-primary" />
                    <span>Mở trong tab mới</span>
                  </a>
                )}

                <button
                  type="button"
                  onClick={() => setIsPdfPreviewOpen(false)}
                  title="Đóng cửa sổ xem nhanh"
                  className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-slate-200/70 hover:text-text-primary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Nội dung trình xem trang PDF hoặc bản đối chiếu trực quan */}
            <div className="flex flex-1 flex-col overflow-hidden bg-slate-100 p-4">
              {/* Thanh đoạn trích đang kiểm chứng */}
              <div className="mb-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs text-slate-800 shadow-2xs">
                <span className="font-semibold text-amber-800">
                  Đoạn trích đang đối chiếu [{citation.source_id}]:{" "}
                </span>
                <span className="italic">&ldquo;{citation.excerpt}&rdquo;</span>
              </div>

              {isDemoDoc ? (
                <div className="flex flex-1 flex-col items-center justify-center rounded-xl border border-border-default bg-white p-8 text-center shadow-inner">
                  <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-slate-50 p-6 text-left shadow-xs">
                    <div className="mb-3 flex items-center justify-between border-b border-slate-200 pb-2 text-xs font-mono text-text-muted">
                      <span>{citation.filename}</span>
                      <span className="font-semibold text-primary">
                        Trang {pageNumber} / Bản xem thử Demo
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-500">
                      ... (Nội dung văn bản phía trên thuộc trang {pageNumber}) ...
                    </p>
                    <mark className="my-3 block rounded-lg border-l-4 border-amber-500 bg-amber-100/90 p-3 text-sm font-medium leading-relaxed text-slate-900">
                      {citation.excerpt}
                    </mark>
                    <p className="text-xs leading-relaxed text-slate-500">
                      ... (Nội dung tiếp theo trên trang {pageNumber} của tài liệu) ...
                    </p>
                  </div>
                </div>
              ) : (
                <iframe
                  title={`PDF Preview ${citation.filename} Trang ${pageNumber}`}
                  src={pdfFileUrl}
                  className="h-full w-full flex-1 rounded-xl border border-border-default bg-white shadow-inner"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
