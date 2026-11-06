import { Sparkles, MessageSquarePlus, ShieldCheck, BookOpen } from "lucide-react";

const SUGGESTED_QUESTIONS = [
  "Người lao động làm đủ 12 tháng được nghỉ phép năm bao nhiêu ngày?",
  "Thời gian thử việc tối đa đối với vị trí trình độ đại học là bao lâu?",
  "Quy định về chế độ cộng thêm ngày phép theo thâm niên làm việc?",
  "Quy trình đăng ký nghỉ phép trên hệ thống nội bộ cần báo trước mấy ngày?",
];

interface EmptyChatStateProps {
  onSelectSuggestion: (question: string) => void;
  selectedDocumentsCount: number;
}

/**
 * [SP5-03.1] Màn hình chào mừng kèm các câu hỏi gợi ý khi phiên hội thoại chưa có tin nhắn.
 */
export function EmptyChatState({
  onSelectSuggestion,
  selectedDocumentsCount,
}: EmptyChatStateProps) {
  return (
    <div className="my-8 flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-default bg-bg-app px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-light text-primary shadow-2xs">
        <Sparkles className="h-6 w-6" />
      </div>

      <h3 className="mt-4 text-lg font-bold text-text-primary">
        Trợ lý Hỏi - Đáp Tài liệu Thông minh (RAG)
      </h3>

      <p className="mt-1.5 max-w-lg text-sm leading-relaxed text-text-secondary">
        Đặt câu hỏi bằng tiếng Việt hoặc tiếng Anh về các tài liệu PDF/DOCX đã
        chọn. Hệ thống chỉ trả lời dựa trên ngữ cảnh thực tế và gắn nhãn trích
        dẫn xác thực{" "}
        <span className="rounded-xs bg-primary-light px-1.5 py-0.5 font-mono text-xs font-semibold text-primary">
          [S1]
        </span>
        ,{" "}
        <span className="rounded-xs bg-primary-light px-1.5 py-0.5 font-mono text-xs font-semibold text-primary">
          [S2]
        </span>{" "}
        tới từng trang.
      </p>

      {/* Thẻ thông tin tính năng nổi bật */}
      <div className="mt-5 grid max-w-lg grid-cols-1 gap-2.5 sm:grid-cols-2">
        <div className="flex items-start gap-2 rounded-xl border border-border-default bg-bg-surface p-3 text-left">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#16A34A]" />
          <div>
            <p className="text-xs font-semibold text-text-primary">
              Chống ảo giác 2 lớp
            </p>
            <p className="mt-0.5 text-[11px] text-text-muted">
              Tự động đối chiếu source_map và từ chối nếu câu hỏi nằm ngoài tài
              liệu.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-2 rounded-xl border border-border-default bg-bg-surface p-3 text-left">
          <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <div>
            <p className="text-xs font-semibold text-text-primary">
              Đang chọn {selectedDocumentsCount} tài liệu
            </p>
            <p className="mt-0.5 text-[11px] text-text-muted">
              Nhấn vào thẻ [S1] trong câu trả lời để xem nguyên văn đoạn trích
              bên phải.
            </p>
          </div>
        </div>
      </div>

      {/* Danh sách các câu hỏi gợi ý ([SP5-03.1]) */}
      <div className="mt-6 w-full max-w-xl">
        <p className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
          Câu hỏi gợi ý để bắt đầu nhanh
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTED_QUESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onSelectSuggestion(suggestion)}
              className="flex items-start gap-2 rounded-xl border border-border-default bg-bg-surface p-3 text-left text-xs font-medium text-text-secondary transition-all hover:border-primary/50 hover:bg-primary-light hover:text-primary hover:shadow-2xs"
            >
              <MessageSquarePlus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
              <span className="line-clamp-2">{suggestion}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

