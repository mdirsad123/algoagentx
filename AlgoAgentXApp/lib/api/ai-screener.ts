import axiosInstance from "../axios";
import { parseApiError } from "./error";

// TypeScript interfaces for AI screener API responses

export interface NewsItem {
  title: string;
  summary: string;
  url: string;
  date: string | Date;
  sentiment_label: "positive" | "negative" | "neutral";
  sentiment_score: number;
  symbol: string;
}

export interface AnnouncementItem {
  title: string;
  summary: string;
  url: string;
  date: string | Date;
  symbol: string;
  exchange: string;
  nse_link?: string | null;
  bse_link?: string | null;
}

export interface TopNewsResponse {
  items: NewsItem[];
  total: number;
  date: string;
  sentiment_type: "positive" | "negative";
}

export interface NewsSearchResponse {
  items: NewsItem[];
  total: number;
  query: string;
  date?: string | null;
}

export interface LatestAnnouncementsResponse {
  items: AnnouncementItem[];
  total: number;
  date?: string | null;
}

export interface AiScreenerJobResponse {
  job_id: string;
  status: string;
  message: string;
  mode: string;
  depth: string;
  policy: string;
  cost: number;
  deducted: number;
  remaining_balance: number;
  remaining_included: number;
  policy_message: string;
  poll_url: string;
}

export interface AiScreenerJobHistoryResponse {
  jobs: Array<{
    job_id: string;
    status: string;
    mode: string;
    depth: string;
    policy: string;
    cost: number;
    deducted: number;
    policy_message?: string | null;
    remaining_balance?: number | null;
    remaining_included?: number | null;
    created_at: string;
    updated_at: string;
    result: any;
  }>;
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
  filters_applied: {
    mode?: string | null;
    depth?: string | null;
    status?: string | null;
    start_date_from?: string | null;
    start_date_to?: string | null;
  };
}

export interface AiScreenerJobStatusResponse {
  job_id: string;
  status: string;
  mode?: string;
  depth?: string;
  policy?: string;
  cost?: number;
  deducted?: number;
  policy_message?: string | null;
  remaining_balance?: number | null;
  remaining_included?: number | null;
  created_at: string;
  updated_at: string;
  result: any;
}

export interface AdminRunScreenerResponse {
  job_id: string;
  status: string;
  message: string;
  type: string;
  triggered_by: string;
  poll_url: string;
}

export interface AiScreenerStatus {
  news: {
    last_run: string | null;
    status: string;
    finished_at: string | null;
    error: string | null;
  };
  announcements: {
    last_run: string | null;
    status: string;
    finished_at: string | null;
    error: string | null;
  };
}

// AI screener API client
export const aiScreenerApi = {
  // Run AI screener job
  runAiScreener: async (
    mode: string,
    depth: string
  ): Promise<AiScreenerJobResponse> => {
    const response = await axiosInstance.post("/api/v1/ai-screener/run", null, {
      params: { mode, depth }
    });
    return response.data;
  },

  // Get AI screener job history
  getAiScreenerHistory: async (
    mode?: string,
    depth?: string,
    status_filter?: string,
    start_date_from?: string,
    start_date_to?: string,
    sort_by: string = "created_at",
    sort_order: "asc" | "desc" = "desc",
    page: number = 1,
    page_size: number = 20
  ): Promise<AiScreenerJobHistoryResponse> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/history", {
      params: {
        mode,
        depth,
        status_filter,
        start_date_from,
        start_date_to,
        sort_by,
        sort_order,
        page,
        page_size
      }
    });
    return response.data;
  },

  // Get AI screener job status by ID
  getAiScreenerJobStatus: async (job_id: string): Promise<AiScreenerJobStatusResponse> => {
    const response = await axiosInstance.get(`/api/v1/ai-screener/${job_id}`);
    return response.data;
  },

  // Get top positive news for a specific date
  getTopPositiveNews: async (
    date: string,
    limit: number = 10
  ): Promise<TopNewsResponse> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/news/top-positive", {
      params: { date, limit }
    });
    return response.data;
  },

  // Get top negative news for a specific date
  getTopNegativeNews: async (
    date: string,
    limit: number = 10
  ): Promise<TopNewsResponse> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/news/top-negative", {
      params: { date, limit }
    });
    return response.data;
  },

  // Search news by query with optional date filter
  searchNews: async (
    query: string,
    date?: string
  ): Promise<NewsSearchResponse> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/news/search", {
      params: { query, date }
    });
    return response.data;
  },

  // Get latest announcements with optional date filter
  getLatestAnnouncements: async (
    date?: string,
    limit: number = 50
  ): Promise<LatestAnnouncementsResponse> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/announcements/latest", {
      params: { date, limit }
    });
    return response.data;
  },

  // Admin endpoint to trigger manual AI screener runs
  adminRunScreener: async (type: string): Promise<AdminRunScreenerResponse> => {
    const response = await axiosInstance.post("/api/v1/ai-screener/admin/run", null, {
      params: { type }
    });
    return response.data;
  },

  // Get AI screener status
  getAiScreenerStatus: async (): Promise<AiScreenerStatus> => {
    const response = await axiosInstance.get("/api/v1/ai-screener/status");
    return response.data;
  }
};