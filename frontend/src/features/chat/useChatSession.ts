import { create } from "zustand";
import type { IConversation, IMessage } from "@/types";
import { SAMPLE_CITATIONS } from "@/features/chat/useActiveCitation";

export const SAMPLE_CONVERSATIONS: IConversation[] = [
  {
    id: "conv-demo-1",
    title: "Quy định nghỉ phép năm và cộng thêm thâm niên",
    created_at: "2026-11-01T00:35:00Z",
  },
  {
    id: "conv-demo-2",
    title: "Thời gian thử việc tối đa đối với trình độ đại học",
    created_at: "2026-11-01T01:10:00Z",
  },
];

export const INITIAL_MESSAGES: IMessage[] = [
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

const DEMO_CONV_2_MESSAGES: IMessage[] = [
  {
    id: "msg-3",
    conversation_id: "conv-demo-2",
    role: "user",
    content: "Thời gian thử việc tối đa đối với vị trí đại học là bao lâu?",
    created_at: "2026-11-01T01:10:00Z",
  },
  {
    id: "msg-4",
    conversation_id: "conv-demo-2",
    role: "assistant",
    content:
      "Theo quy định tại **Điều 25 Bộ luật Lao động 2019**, thời gian thử việc không quá **60 ngày** đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên [S1].",
    sources: [SAMPLE_CITATIONS[0]],
    created_at: "2026-11-01T01:10:03Z",
  },
];

interface ChatSessionState {
  conversations: IConversation[];
  activeConversationId: string | null;
  messages: IMessage[];
  isSending: boolean;
  isLoadingHistory: boolean;
  setConversations: (conversations: IConversation[]) => void;
  upsertConversation: (conversation: IConversation) => void;
  removeConversation: (conversationId: string) => void;
  selectConversation: (conversationId: string, messages?: IMessage[]) => void;
  startNewConversation: () => void;
  setMessages: (messages: IMessage[]) => void;
  addMessage: (message: IMessage) => void;
  resetSession: () => void;
  setIsSending: (sending: boolean) => void;
  setIsLoadingHistory: (loading: boolean) => void;
}

export const useChatSession = create<ChatSessionState>((set) => ({
  conversations: SAMPLE_CONVERSATIONS,
  activeConversationId: "conv-demo-1",
  messages: INITIAL_MESSAGES,
  isSending: false,
  isLoadingHistory: false,

  setConversations: (conversations) => set({ conversations }),

  upsertConversation: (conversation) =>
    set((state) => {
      const exists = state.conversations.some((c) => c.id === conversation.id);
      const updated = exists
        ? state.conversations.map((c) =>
            c.id === conversation.id ? conversation : c
          )
        : [conversation, ...state.conversations];
      return {
        conversations: updated,
        activeConversationId: conversation.id,
      };
    }),

  removeConversation: (conversationId) =>
    set((state) => {
      const remaining = state.conversations.filter(
        (c) => c.id !== conversationId
      );
      const isRemovingActive = state.activeConversationId === conversationId;
      return {
        conversations: remaining,
        activeConversationId: isRemovingActive
          ? null
          : state.activeConversationId,
        messages: isRemovingActive ? [] : state.messages,
      };
    }),

  selectConversation: (conversationId, loadedMessages) =>
    set(() => {
      if (loadedMessages) {
        return {
          activeConversationId: conversationId,
          messages: loadedMessages,
        };
      }
      if (conversationId === "conv-demo-1") {
        return {
          activeConversationId: conversationId,
          messages: INITIAL_MESSAGES,
        };
      }
      if (conversationId === "conv-demo-2") {
        return {
          activeConversationId: conversationId,
          messages: DEMO_CONV_2_MESSAGES,
        };
      }
      return {
        activeConversationId: conversationId,
        messages: [],
      };
    }),

  startNewConversation: () =>
    set({
      activeConversationId: null,
      messages: [],
    }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  resetSession: () =>
    set({
      activeConversationId: null,
      messages: [],
    }),

  setIsSending: (sending) => set({ isSending: sending }),
  setIsLoadingHistory: (loading) => set({ isLoadingHistory: loading }),
}));
