import { BookOpenCheck, X, Layers } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SourceCard } from "@/components/citations/SourceCard";
import { SourceDetailViewer } from "@/components/citations/SourceDetailViewer";
import { useActiveCitation } from "@/features/chat/useActiveCitation";

/**
 * [SP5-01.3 & SP5-04.3 & SP5-04.4] Panel Nguồn trích dẫn bên phải (rộng 360px, đóng/mở mượt mà).
 * - Hiển thị SourceDetailViewer chứa đầy đủ đoạn văn bản gốc (excerpt) được tô sáng (highlight)
 *   và nút mở xem nhanh trang PDF tương ứng.
 * - Hiển thị danh sách SourceCard của toàn bộ nguồn trong câu trả lời hiện tại để chuyển đổi nhanh.
 */
export function RightSourcePanel() {
  const {
    activeCitation,
    activeMessageSources,
    isSourcePanelOpen,
    setActiveCitation,
    closeSourcePanel,
  } = useActiveCitation();

  return (
    <aside
      aria-label="Panel chi tiết nguồn trích dẫn"
      aria-hidden={!isSourcePanelOpen}
      className={`shrink-0 overflow-hidden bg-[#F1F5F9] transition-all duration-300 ease-in-out ${
        isSourcePanelOpen
          ? "w-[360px] border-l border-border-default opacity-100"
          : "w-0 border-l-0 opacity-0 pointer-events-none"
      }`}
    >
      <div className="flex h-full w-[360px] flex-col p-4">
        {/* Thanh tiêu đề Panel Nguồn ([SP5-01.3]) */}
        <div className="flex items-center justify-between border-b border-border-default pb-3">
          <div className="flex items-center gap-2">
            <BookOpenCheck className="h-4 w-4 text-primary" />
            <h2 className="text-[15px] font-semibold text-text-primary">
              Chi tiết nguồn trích dẫn
            </h2>
          </div>

          <button
            type="button"
            onClick={closeSourcePanel}
            title="Đóng Panel nguồn trích dẫn"
            className="rounded-lg p-1 text-text-muted transition-colors hover:bg-slate-200/70 hover:text-text-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <ScrollArea className="mt-4 flex-1 pr-1">
          {activeCitation ? (
            <div className="space-y-4">
              {/* [SP5-04.3 & SP5-04.4] Khung chi tiết nguồn đang chọn kèm Highlight & Xem nhanh PDF */}
              <SourceDetailViewer citation={activeCitation} />

              {/* Danh sách tất cả các nguồn trong câu trả lời hiện tại */}
              {activeMessageSources.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-text-muted" />
                    <p className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                      Nguồn trong câu trả lời ({activeMessageSources.length})
                    </p>
                  </div>
                  <div className="space-y-2">
                    {activeMessageSources.map((item) => {
                      const isCurrent =
                        activeCitation.source_id === item.source_id &&
                        activeCitation.document_id === item.document_id;
                      return (
                        <SourceCard
                          key={`${item.source_id}-${item.document_id}-${item.chunk_index ?? 0}`}
                          source={item}
                          compact={false}
                          isSelected={isCurrent}
                          onClick={(selected) =>
                            setActiveCitation(selected, activeMessageSources)
                          }
                        />
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border-default bg-bg-surface p-6 text-center">
              <BookOpenCheck className="h-8 w-8 text-text-muted" />
              <p className="mt-2 text-sm font-medium text-text-primary">
                Chưa chọn nguồn trích dẫn
              </p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                Nhấn vào nhãn{" "}
                <span className="font-mono font-semibold text-primary">
                  [S1]
                </span>
                ,{" "}
                <span className="font-mono font-semibold text-primary">
                  [S2]
                </span>{" "}
                trong câu trả lời của AI để đối chiếu tên tệp, số trang PDF và
                đoạn văn bản gốc.
              </p>
            </div>
          )}
        </ScrollArea>
      </div>
    </aside>
  );
}
