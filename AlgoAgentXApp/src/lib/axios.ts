import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  message?: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_SERVER?.replace(/\/+$/, "") || "http://localhost:8000";

export const getStoredAccessToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredAccessToken();
  const shouldAttachAuth = (config as AxiosRequestConfig & { auth?: boolean }).auth !== false;

  if (token && shouldAttachAuth) {
    config.headers = config.headers || ({} as any);
    (config.headers as any).Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<any>) => {
    const detail = error.response?.data?.detail;

    let message = "Request failed";
    if (typeof detail === "string" && detail.trim()) {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      const issues = detail
        .map((item: any) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") return item.msg || item.message || JSON.stringify(item);
          return String(item);
        })
        .filter(Boolean)
        .join("; ");
      message = issues || error.message || "Request failed";
    } else if (detail && typeof detail === "object") {
      message = detail.message || detail.error || error.response?.data?.message || error.message || "Request failed";
    } else if (typeof error.response?.data?.message === "string" && error.response?.data?.message.trim()) {
      message = error.response.data.message;
    } else if (error.message) {
      message = error.message;
    }

    error.message = message;
    return Promise.reject(error);
  }
);

const unwrapResponse = <T>(payload: ApiEnvelope<T> | T): T => {
  if (
    payload &&
    typeof payload === "object" &&
    "success" in (payload as Record<string, unknown>)
  ) {
    return ((payload as ApiEnvelope<T>).data ?? null) as T;
  }
  return payload as T;
};

export const apiGet = async <T>(
  url: string,
  config?: AxiosRequestConfig & { auth?: boolean }
): Promise<T> => {
  const response = await apiClient.get<ApiEnvelope<T> | T>(url, config);
  return unwrapResponse<T>(response.data);
};

export const apiPost = async <T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig & { auth?: boolean }
): Promise<T> => {
  const response = await apiClient.post<ApiEnvelope<T> | T>(url, body, config);
  return unwrapResponse<T>(response.data);
};

export const apiPatch = async <T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig & { auth?: boolean }
): Promise<T> => {
  const response = await apiClient.patch<ApiEnvelope<T> | T>(url, body, config);
  return unwrapResponse<T>(response.data);
};

export default apiClient;