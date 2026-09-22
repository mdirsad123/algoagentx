import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import { API_TIMEOUT_MS } from "./api-timeouts";
import { getApiBaseUrl } from "./api-base";
import { clearAuthSession } from "./auth/session";

type ApiEnvelope<T> = {
  success?: boolean;
  data?: T;
  message?: string;
};

const API_BASE_URL = getApiBaseUrl();

const SLOW_REQUEST_MESSAGE =
  "Request is still taking longer than expected. Please retry, or wait for backend to finish if this is a heavy report/backtest.";

export const getStoredAccessToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredAccessToken();
  const shouldAttachAuth = (config as AxiosRequestConfig & { auth?: boolean }).auth !== false;

  config.headers = config.headers || ({} as any);

  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete (config.headers as any)["Content-Type"];
    delete (config.headers as any)["content-type"];
  }

  if (token && shouldAttachAuth) {
    (config.headers as any).Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<any>) => {
    const detail = error.response?.data?.detail;
    const isTimeoutError =
      error.code === "ECONNABORTED" ||
      String(error.message || "").toLowerCase().includes("timeout");

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
    } else if (isTimeoutError) {
      message = SLOW_REQUEST_MESSAGE;
    } else if (error.message) {
      message = error.message;
    }

    if (error.response?.status === 401 || error.response?.status === 403) {
      const isPublicRequest = (error.config as AxiosRequestConfig & { auth?: boolean } | undefined)?.auth === false;
      if (typeof window !== "undefined" && !isPublicRequest) {
        const pathname = window.location.pathname;
        const path = pathname + window.location.search;
        const isPublicPage =
          pathname === "/" ||
          pathname === "/login" ||
          pathname === "/register" ||
          pathname.startsWith("/auth/");

        if (!isPublicPage) {
          clearAuthSession();
          const loginPath = pathname.startsWith("/admin") ? "/auth/admin-login" : "/auth/login";
          const target = `${loginPath}?redirect=${encodeURIComponent(path)}`;
          window.setTimeout(() => window.location.replace(target), 0);
        }
      }
      message = error.response?.status === 403 ? "You do not have permission to access this page." : "Your session has expired. Please sign in again.";
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

export const apiDelete = async <T = unknown>(
  url: string,
  config?: AxiosRequestConfig & { auth?: boolean }
): Promise<T> => {
  const response = await apiClient.delete<ApiEnvelope<T> | T>(url, config);
  return unwrapResponse<T>(response.data);
};

export default apiClient;
