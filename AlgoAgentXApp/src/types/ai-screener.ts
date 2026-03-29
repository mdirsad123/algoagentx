import { UUID } from "crypto";

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

// Component props interfaces
export interface NewsTableProps {
  title: string;
  sentimentType: "positive" | "negative";
  loading: boolean;
  data: NewsItem[];
  onRefresh: () => void;
}

export interface AnnouncementsTableProps {
  loading: boolean;
  data: AnnouncementItem[];
  onRefresh: () => void;
}

export interface SearchTableProps {
  loading: boolean;
  data: NewsItem[];
  query: string;
  onSearch: (query: string) => void;
  onRefresh: () => void;
}