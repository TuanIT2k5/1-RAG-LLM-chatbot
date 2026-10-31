import type { IHealthStatus } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.message || `Lỗi kết nối máy chủ (${response.status})`
    );
  }

  return response.json() as Promise<T>;
}

export async function fetchHealthStatus(): Promise<IHealthStatus> {
  return apiRequest<IHealthStatus>("/health");
}

