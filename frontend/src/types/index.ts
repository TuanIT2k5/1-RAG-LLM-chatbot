export type DocumentStatus = "processing" | "processed" | "failed";

export interface IDocument {
  id: string;
  user_id?: string | null;
  filename: string;
  storage_path: string;
  file_type: "pdf" | "docx";
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
}

export interface ICitationSource {
  source_id: string;
  document_id: string;
  filename: string;
  page_number?: number | null;
  chunk_index?: number | null;
  chunk_id?: string | null;
  excerpt: string;
  score?: number | null;
}

export interface IMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ICitationSource[];
  created_at: string;
}

export interface IConversation {
  id: string;
  user_id?: string | null;
  title: string;
  created_at: string;
}

export interface IHealthStatus {
  status: string;
  database?: string;
  app_name: string;
  version: string;
  environment: string;
  llm_provider: string;
  embedding_model: string;
  timestamp: string;
}

