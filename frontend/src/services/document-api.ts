import type { IDocument } from "@/types";
import { apiRequest } from "@/services/api-client";

export interface IDocumentListResponse {
  total: number;
  items: IDocument[];
}

export async function getDocuments(): Promise<IDocumentListResponse> {
  return apiRequest<IDocumentListResponse>("/documents");
}

