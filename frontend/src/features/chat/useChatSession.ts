import { create } from "zustand";
import type { IMessage } from "@/types";
import { SAMPLE_CITATIONS } from "@/features/chat/useActiveCitation";

const INITIAL_MESSAGES: IMessage[] = [
  {
    id: "msg-1",
    conversation_id: "conv-demo-1",
    role: "user",
    content:
      "Người lao động làm đủ 12 tháng được nghỉ phép năm bao nhiêu ngày và chế độ cộng thêm thâm niên thế nào?",
    created_at: "2026-11-01T00:35:00Z",
  },
  {
    id: "msg-2",
    conversation_id: "conv-demo-1",
    role: "assistant",
    content:
      "Theo **Điều 113 Bộ luật Lao động 2019**, người lao động làm việc đủ 12 tháng cho một người sử dụng lao động thì được nghỉ hằng năm hưởng nguyên lương **12 ngày làm việc** đối với điều kiện bình thường [S1].\n\nNgoài ra, theo **Nội quy Công ty**, cứ đủ **05 năm làm việc liên tục**, số ngày nghỉ hằng năm của nhân viên được tăng thêm **01 ngày** hưởng nguyên lương [S2].",
    sources: SAMPLE_CITATIONS,
    created_at: "2026-11-01T00:35:04Z",
  },
];

interface ChatSessionState {
  messages: IMessage[];
  addMessage: (message: IMessage) => void;
  resetSession: () => void;
}

export const useChatSession = create<ChatSessionState>((set) => ({
  messages: INITIAL_MESSAGES,
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  resetSession: () => set({ messages: [] }),
}));

