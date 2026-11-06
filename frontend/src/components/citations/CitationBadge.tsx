import type { ICitationSource } from "@/types";

interface CitationBadgeProps {
  source: ICitationSource;
  isActive?: boolean;
  onClick: (source: ICitationSource) => void;
}

/**
 * [SP5-04.1] Nút nhãn trích dẫn tương tác [S1], [S2]... ngay trong dòng văn bản của AI.
 * - Hiển thị nổi bật với màu xanh dương đặc trưng (#EFF6FF nền, #2563EB chữ & viền).
 * - Có hiệu ứng vòng sáng (ring) khi đang là nguồn được chọn xem trong Panel bên phải.
 */
export function CitationBadge({
  source,
  isActive = false,
  onClick,
}: CitationBadgeProps) {
  const locationLabel = source.page_number
    ? `Trang ${source.page_number}`
    : `Đoạn #${source.chunk_index ?? 0}`;

  return (
    <button
      type="button"
      onClick={() => onClick(source)}
      title={`Xem nguồn [${source.source_id}]: ${source.filename} (${locationLabel})`}
      aria-label={`Trích dẫn ${source.source_id} từ ${source.filename} - ${locationLabel}`}
      className={`mx-0.5 inline-flex cursor-pointer items-center gap-0.5 rounded-md border px-1.5 py-0.5 font-mono text-xs font-semibold transition-all select-none ${
        isActive
          ? "border-primary bg-primary text-white shadow-xs ring-2 ring-primary/35"
          : "border-primary/35 bg-primary-light text-primary hover:border-primary hover:bg-primary hover:text-white"
      }`}
    >
      <span>[{source.source_id}]</span>
    </button>
  );
}

