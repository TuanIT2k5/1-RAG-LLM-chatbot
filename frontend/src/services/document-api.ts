import type { IDocument, DocumentStatus } from "@/types";
import {
  API_BASE_URL,
  ApiClientError,
  apiRequest,
  buildApiClientError,
  type IApiErrorPayload,
} from "@/services/api-client";

export interface IDocumentListResponse {
  total: number;
  items: IDocument[];
}

export interface IDocumentUploadResponse {
  message: string;
  document: IDocument;
}

export interface IDocumentDeleteResponse {
  message: string;
  document_id: string;
}

/**
 * Kiểm tra kiểu dữ liệu runtime cho đối tượng IDocument trả về từ Backend.
 */
function normalizeDocument(raw: IDocument): IDocument {
  return {
    id: String(raw.id),
    filename: String(raw.filename),
    storage_path: String(raw.storage_path || ""),
    file_type: raw.file_type === "docx" ? "docx" : "pdf",
    file_size: Number(raw.file_size || 0),
    status:
      raw.status === "processed" ||
      raw.status === "processing" ||
      raw.status === "failed"
        ? raw.status
        : "processing",
    chunk_count: Number(raw.chunk_count || 0),
    error_message: raw.error_message ?? null,
    created_at: String(raw.created_at || new Date().toISOString()),
    updated_at: raw.updated_at ? String(raw.updated_at) : undefined,
  };
}

/**
 * [SP5-05.2] Lấy danh sách tài liệu từ GET /api/documents
 */
export async function fetchDocuments(
  status?: DocumentStatus
): Promise<IDocumentListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await apiRequest<IDocumentListResponse>(`/documents${query}`, {
    silentError: true,
  });

  const items = Array.isArray(res?.items)
    ? res.items.map(normalizeDocument)
    : [];
  return {
    total: typeof res?.total === "number" ? res.total : items.length,
    items,
  };
}

/**
 * [SP5-05.2] Lấy thông tin chi tiết 1 tài liệu từ GET /api/documents/{id}
 */
export async function fetchDocumentDetail(
  documentId: string
): Promise<IDocument> {
  const doc = await apiRequest<IDocument>(
    `/documents/${encodeURIComponent(documentId)}`
  );
  return normalizeDocument(doc);
}

/**
 * [SP5-04.4] Tạo URL truy cập trực tiếp tệp tài liệu gốc (kèm #page=X cho PDF)
 */
export function getDocumentFileUrl(
  documentId: string,
  pageNumber?: number | null
): string {
  const baseUrl = `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/file`;
  if (typeof pageNumber === "number" && pageNumber > 0) {
    return `${baseUrl}#page=${pageNumber}`;
  }
  return baseUrl;
}

/**
 * [SP5-05.2] Xóa đồng bộ tài liệu qua DELETE /api/documents/{id}
 */
export async function deleteDocumentById(
  documentId: string
): Promise<IDocumentDeleteResponse> {
  return apiRequest<IDocumentDeleteResponse>(
    `/documents/${encodeURIComponent(documentId)}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * [SP5-02.1, SP5-02.2 & SP5-05.2] Gửi tệp multipart/form-data lên POST /api/documents/upload
 * có hỗ trợ callback theo dõi phần trăm tiến trình tải lên (onProgress) và chuẩn hóa lỗi ApiClientError.
 */
export function uploadDocumentFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<IDocumentUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE_URL}/documents/upload`, true);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && event.total > 0) {
          const percent = Math.min(
            95,
            Math.round((event.loaded / event.total) * 100)
          );
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(xhr.responseText || "{}");
      } catch {
        parsed = {};
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        if (onProgress) onProgress(100);
        const rawDoc = (parsed.document || parsed) as unknown as IDocument;
        resolve({
          message:
            typeof parsed.message === "string"
              ? parsed.message
              : "Tải lên và lập chỉ mục tài liệu thành công.",
          document: normalizeDocument(rawDoc),
        });
      } else {
        const apiError = buildApiClientError(
          xhr.status,
          parsed as unknown as IApiErrorPayload
        );
        reject(apiError);
      }
    };

    xhr.onerror = () => {
      reject(
        new ApiClientError({
          message:
            "Không thể kết nối tới máy chủ Backend khi tải tệp. Vui lòng kiểm tra kết nối mạng.",
          status: 0,
          errorCode: "NETWORK_ERROR",
          isNetworkError: true,
        })
      );
    };

    xhr.send(formData);
  });
}
