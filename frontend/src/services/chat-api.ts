import type { ICitationSource } from "@/types";
import { apiRequest } from "@/services/api-client";

export interface IChatRequestPayload {
  question: string;
  document_ids?: string[];
  conversation_id?: string;
}

export interface IChatResponsePayload {
  conversation_id: string;
  message_id?: string;
  question: string;
  answer: string;
  sources: ICitationSource[];
  created_at: string;
}

export async function sendChatMessage(
  payload: IChatRequestPayload
): Promise<IChatResponsePayload> {
  return apiRequest<IChatResponsePayload>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

