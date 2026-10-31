import { create } from "zustand";
import type { ICitationSource } from "@/types";

export const SAMPLE_CITATIONS: ICitationSource[] = [
  {
    source_id: "S1",
    document_id: "doc-demo-1",
    filename: "Bo_luat_Lao_dong_2019.pdf",
    page_number: 45,
    chunk_index: 12,
    excerpt:
      "Điều 113. Nghỉ hằng năm: Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động thì được nghỉ hằng năm, hưởng nguyên lương theo hợp đồng lao động là 12 ngày làm việc đối với người làm công việc trong điều kiện bình thường...",
    score: 0.94,
  },
  {
    source_id: "S2",
    document_id: "doc-demo-2",
    filename: "Noi_quy_Cong_ty_2026.docx",
    page_number: null,
    chunk_index: 4,
    excerpt:
      "Mục 4.2. Chế độ cộng thêm ngày phép thâm niên: Cứ đủ 05 năm làm việc liên tục tại Công ty, số ngày nghỉ hằng năm của nhân viên được tăng thêm tương ứng 01 ngày hưởng nguyên lương.",
    score: 0.88,
  },
];

interface ActiveCitationState {
  activeCitation: ICitationSource | null;
  setActiveCitation: (citation: ICitationSource | null) => void;
}

export const useActiveCitation = create<ActiveCitationState>((set) => ({
  activeCitation: SAMPLE_CITATIONS[0],
  setActiveCitation: (citation) => set({ activeCitation: citation }),
}));

