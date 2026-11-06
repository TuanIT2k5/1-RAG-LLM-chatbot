import { FileText, FileCode2 } from "lucide-react";
import type { ICitationSource } from "@/types";

interface SourceCardProps {
  source: ICitationSource;
  isSelected?: boolean;
  compact?: boolean;
  onClick: (source: ICitationSource) => void;
}

/**
 * [SP5-04.2] Thẻ nguồn trích dẫn thu gọn (SourceCard).
 * - Hiển thị bên dưới mỗi câu trả lời của AI hoặc trong danh sách nguồn của Panel bên phải.
 * - Ghi rõ mã nguồn [S1], tên tệp và số trang PDF ("Trang X") hoặc thứ tự đoạn DOCX ("Đoạn #Y").
 */
export function SourceCard({
  source,
  isSelected = false,
  compact = true,
  onClick,
}: SourceCardProps) {
  const isPdf = source.filename.toLowerCase().endsWith(".pdf");
  const locationText = source.page_number
    ? `Trang ${source.page_number}`
    : `Đoạn #${source.chunk_index ?? 0}`;

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => onClick(source)}
        title={`Nhấn để đối chiếu đoạn trích gốc từ ${source.filename} (${locationText})`}
        className={`group inline-flex max-w-full items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-left text-xs transition-all ${
          isSelected
            ? "border-primary bg-primary text-white shadow-xs ring-2 ring-primary/30"
            : "border-primary/25 bg-primary-light/70 text-text-primary hover:border-primary hover:bg-primary-light"
        }`}
      >
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-bold ${
            isSelected
              ? "bg-white/20 text-white"
              : "bg-primary/15 text-primary group-hover:bg-primary group-hover:text-white"
          }`}
        >
          [{source.source_id}]
        </span>

        {isPdf ? (
          <FileText
            className={`h-3.5 w-3.5 shrink-0 ${
              isSelected ? "text-white" : "text-red-600"
            }`}
          />
        ) : (
          <FileCode2
            className={`h-3.5 w-3.5 shrink-0 ${
              isSelected ? "text-white" : "text-blue-600"
            }`}
          />
        )}

        <span className="max-w-[170px] truncate font-medium">
          {source.filename}
        </span>

        <span
          className={`shrink-0 font-mono text-[11px] font-semibold ${
            isSelected ? "text-blue-100" : "text-primary"
          }`}
        >
          • {locationText}
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onClick(source)}
      className={`w-full rounded-xl border p-2.5 text-left text-xs transition-all ${
        isSelected
          ? "border-primary bg-primary-light font-medium text-primary shadow-2xs ring-1 ring-primary/30"
          : "border-border-default bg-bg-surface text-text-secondary hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-bold ${
              isSelected
                ? "bg-primary text-white"
                : "bg-primary-light text-primary"
            }`}
          >
            [{source.source_id}]
          </span>
          <span className="truncate font-semibold text-text-primary">
            {source.filename}
          </span>
        </div>

        <span className="shrink-0 rounded-md bg-slate-200/70 px-1.5 py-0.5 font-mono text-[11px] font-medium text-text-secondary">
          {locationText}
        </span>
      </div>

      <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-text-muted">
        &ldquo;{source.excerpt}&rdquo;
      </p>
    </button>
  );
}

