import type { IHealthStatus } from "@/types";

/**
 * [SP5-05.1] Địa chỉ cơ sở của Backend API đọc từ biến môi trường VITE_API_BASE_URL
 * (mặc định là "/api" để hoạt động mượt với Vite Proxy và Nginx Reverse Proxy).
 */
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") ||
  "/api";

const DEFAULT_TIMEOUT_MS = 35000;

export interface IApiErrorPayload {
  error_code?: string;
  message?: string;
  detail?: string | Record<string, unknown>;
}

/**
 * Lớp lỗi chuẩn hóa cho toàn bộ tầng giao tiếp API ở Frontend.
 */
export class ApiClientError extends Error {
  public readonly status: number;
  public readonly errorCode: string;
  public readonly isNetworkError: boolean;

  constructor(params: {
    message: string;
    status?: number;
    errorCode?: string;
    isNetworkError?: boolean;
  }) {
    super(params.message);
    this.name = "ApiClientError";
    this.status = params.status ?? 0;
    this.errorCode = params.errorCode ?? "UNKNOWN_ERROR";
    this.isNetworkError = Boolean(params.isNetworkError);
  }
}

export type ApiErrorListener = (error: ApiClientError) => void;

const errorListeners = new Set<ApiErrorListener>();

/**
 * Đăng ký lắng nghe lỗi API tập trung (phục vụ Toast Notification hoặc logging).
 */
export function subscribeApiErrors(listener: ApiErrorListener): () => void {
  errorListeners.add(listener);
  return () => {
    errorListeners.delete(listener);
  };
}

function notifyErrorListeners(error: ApiClientError): void {
  errorListeners.forEach((listener) => {
    try {
      listener(error);
    } catch {
      // Không làm gián đoạn luồng chính nếu listener gặp lỗi
    }
  });
}

/**
 * Bộ phân tích lỗi tập trung từ HTTP status và JSON body của FastAPI Backend.
 */
export function buildApiClientError(
  status: number,
  body: IApiErrorPayload | null
): ApiClientError {
  const errorCode =
    (typeof body?.error_code === "string" && body.error_code) ||
    (status === 413
      ? "FILE_TOO_LARGE"
      : status === 400
      ? "INVALID_FILE"
      : status === 422
      ? "VALIDATION_ERROR"
      : status === 404
      ? "NOT_FOUND"
      : status >= 500
      ? "SERVER_ERROR"
      : "HTTP_ERROR");

  let message =
    (typeof body?.message === "string" && body.message) ||
    (typeof body?.detail === "string" && body.detail) ||
    "";

  if (!message) {
    if (status === 413) {
      message = "Tệp tải lên vượt quá dung lượng tối đa cho phép (20MB).";
    } else if (status === 404) {
      message = "Không tìm thấy dữ liệu yêu cầu trên máy chủ.";
    } else if (status >= 500) {
      message = `Máy chủ xử lý gặp sự cố (HTTP ${status}). Vui lòng thử lại sau.`;
    } else {
      message = `Yêu cầu không hợp lệ (HTTP ${status}).`;
    }
  }

  return new ApiClientError({
    message,
    status,
    errorCode,
    isNetworkError: false,
  });
}

export interface ApiRequestOptions extends RequestInit {
  timeoutMs?: number;
  silentError?: boolean;
}

/**
 * [SP5-05.1] Hàm gọi Fetch API trung tâm có hỗ trợ Timeout, chuẩn hóa Header
 * và bộ bắt lỗi tập trung (Centralized Error Interceptor).
 */
export async function apiRequest<T>(
  endpoint: string,
  options?: ApiRequestOptions
): Promise<T> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    silentError = false,
    headers,
    ...restOptions
  } = options || {};

  const controller = new AbortController();
  const timerId = window.setTimeout(() => controller.abort(), timeoutMs);

  const normalizedEndpoint = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;

  try {
    const response = await fetch(`${API_BASE_URL}${normalizedEndpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...(headers || {}),
      },
      signal: controller.signal,
      ...restOptions,
    });

    if (!response.ok) {
      const errorBody = (await response
        .json()
        .catch(() => null)) as IApiErrorPayload | null;
      const apiError = buildApiClientError(response.status, errorBody);
      if (!silentError) {
        notifyErrorListeners(apiError);
      }
      throw apiError;
    }

    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }

    const isAbort = err instanceof DOMException && err.name === "AbortError";
    const networkError = new ApiClientError({
      message: isAbort
        ? "Yêu cầu tới máy chủ quá thời gian chờ (Timeout). Vui lòng thử lại."
        : "Không thể kết nối tới máy chủ Backend. Vui lòng kiểm tra kết nối mạng.",
      status: 0,
      errorCode: isAbort ? "REQUEST_TIMEOUT" : "NETWORK_ERROR",
      isNetworkError: true,
    });

    if (!silentError) {
      notifyErrorListeners(networkError);
    }
    throw networkError;
  } finally {
    window.clearTimeout(timerId);
  }
}

export async function fetchHealthStatus(): Promise<IHealthStatus> {
  return apiRequest<IHealthStatus>("/health", { silentError: true });
}
