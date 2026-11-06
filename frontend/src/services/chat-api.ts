import type {
  ICitationSource,
  IConversation,
  IMessage,
} from "@/types";
import { apiRequest } from "@/services/api-client";

export interface IChatRequestPayload {
  question: string;
  document_ids?: string[] | null;
  conversation_id?: string | null;
  top_k?: number;
}

export interface IChatResponsePayload {
  conversation_id: string;
  message_id?: string | null;
  question: string;
  answer: string;
  sources: ICitationSource[];
  created_at: string;
}

export interface IConversationListResponse {
  total: number;
  items: IConversation[];
}

export interface IConversationHistoryResponse {
  conversation: IConversation;
  messages: IMessage[];
}

function normalizeCitationSource(raw: ICitationSource): ICitationSource {
  return {
    source_id: String(raw.source_id || "S1"),
    document_id: String(raw.document_id || ""),
    filename: String(raw.filename || "Tài liệu"),
    page_number:
      typeof raw.page_number === "number" ? raw.page_number : null,
    chunk_index:
      typeof raw.chunk_index === "number" ? raw.chunk_index : 0,
    excerpt: String(raw.excerpt || ""),
    score: typeof raw.score === "number" ? raw.score : undefined,
  };
}

function normalizeMessage(raw: IMessage, fallbackConvId?: string): IMessage {
  return {
    id: String(raw.id),
    conversation_id: String(raw.conversation_id || fallbackConvId || ""),
    role: raw.role === "user" ? "user" : "assistant",
    content: String(raw.content || ""),
    sources: Array.isArray(raw.sources)
      ? raw.sources.map(normalizeCitationSource)
      : [],
    created_at: String(raw.created_at || new Date().toISOString()),
  };
}

/**
 * [SP5-05.2] Gửi câu hỏi hỏi đáp RAG tới POST /api/chat
 */
export async function sendChatMessage(
  payload: IChatRequestPayload
): Promise<IChatResponsePayload> {
  const res = await apiRequest<IChatResponsePayload>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return {
    conversation_id: String(res.conversation_id),
    message_id: res.message_id ? String(res.message_id) : null,
    question: String(res.question || payload.question),
    answer: String(res.answer || ""),
    sources: Array.isArray(res.sources)
      ? res.sources.map(normalizeCitationSource)
      : [],
    created_at: String(res.created_at || new Date().toISOString()),
  };
}

/**
 * [SP5-05.2 & SP5-05.3] Lấy danh sách các phiên hội thoại đã lưu từ GET /api/conversations
 */
export async function fetchConversations(
  skip = 0,
  limit = 50
): Promise<IConversationListResponse> {
  const res = await apiRequest<IConversationListResponse>(
    `/conversations?skip=${skip}&limit=${limit}`,
    { silentError: true }
  );

  const items = Array.isArray(res?.items) ? res.items : [];
  return {
    total: typeof res?.total === "number" ? res.total : items.length,
    items,
  };
}

/**
 * [SP5-05.2 & SP5-05.3] Lấy toàn bộ lịch sử tin nhắn và nguồn trích dẫn của 1 phiên hội thoại
 * từ GET /api/conversations/{id}/messages
 */
export async function fetchConversationMessages(
  conversationId: string
): Promise<IConversationHistoryResponse> {
  const res = await apiRequest<IConversationHistoryResponse>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`
  );

  const convId = String(res.conversation?.id || conversationId);
  return {
    conversation: {
      id: convId,
      title: String(res.conversation?.title || "Cuộc trò chuyện"),
      created_at: String(
        res.conversation?.created_at || new Date().toISOString()
      ),
      updated_at: res.conversation?.updated_at,
    },
    messages: Array.isArray(res.messages)
      ? res.messages.map((m) => normalizeMessage(m, convId))
      : [],
  };
}

/**
 * [SP5-05.2 & SP5-05.3] Xóa một phiên hội thoại qua DELETE /api/conversations/{id}
 */
export async function deleteConversationById(
  conversationId: string
): Promise<{ message: string; conversation_id: string }> {
  return apiRequest<{ message: string; conversation_id: string }>(
    `/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
    }
  );
}
