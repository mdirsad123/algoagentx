import axiosInstance from "../axios";

const unwrap = <T>(response: any): T => {
  const payload = response?.data;
  return payload?.success ? payload.data : payload;
};

export interface AdminMetrics {
  users: { total: number; active: number; recent: any[] };
  payments: { total: number; revenue: number; recent: any[] };
  credits: { total: number; active_subscriptions: number };
  strategies?: { pending: number };
  backtests?: { total: number };
  orders?: { total: number; recent: any[] };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip?: number;
  limit?: number;
  page?: number;
  page_size?: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  fullname?: string;
  mobile?: string;
  plan?: string;
  credits?: number;
}

export interface Payment {
  id: string;
  user_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_method: string;
  razorpay_order_id?: string;
  razorpay_payment_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  plan_code: string;
  billing_period: string;
  price_inr: number;
  included_credits: number;
  status: string;
  start_at: string;
  end_at: string;
  created_at: string;
  updated_at?: string;
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  user_email?: string;
  credits?: number;
  type: string;
  reason?: string;
  created_at: string;
}

export interface Order {
  id: string;
  user_id: string;
  order_number: string;
  status: string;
  total_amount: number;
  currency: string;
  payment_method: string;
  created_at: string;
  updated_at?: string;
  user_email: string;
  user_name: string;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_type: string;
  product_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  product_name?: string;
  product_description?: string;
}

export type StrategyRequestStatus =
  | "UNDER_DEVELOPMENT"
  | "NEEDS_CLARIFICATION"
  | "REJECTED"
  | "DEPLOYED";

export type StrategyVisibility = "PUBLIC" | "PRIVATE";

export interface StrategyRequest {
  id: string;
  title: string;
  name?: string;
  strategy_type?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  indicators?: Record<string, any> | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  risk_rules?: string | null;
  notes?: string | null;
  description?: string | null;
  status: StrategyRequestStatus | string;
  user_id?: string;
  user_email?: string | null;
  user_name?: string | null;
  admin_notes?: string | null;
  assigned_to?: string | null;
  deployed_strategy_id?: string | null;
  deployedStrategyId?: string | null;
  created_at: string;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
}

export interface ImplementedStrategy {
  id: string;
  name: string;
  description?: string | null;
  strategy_type?: string | null;
  strategyType?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  winRate?: number | null;
  sharpeRatio?: number | null;
  maxDrawdown?: number | null;
  totalTrades?: number | null;
  profitFactor?: number | null;
  parameters?: Record<string, any> | null;
  visibility?: string | null;
  status?: string | null;
  source_request_id?: string | null;
  sourceRequestId?: string | null;
  created_by?: string | null;
  published_by?: string | null;
  created_at: string;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
}

export interface StrategyRequestsResponse {
  items: StrategyRequest[];
  implemented: ImplementedStrategy[];
  total: number;
  skip: number;
  limit: number;
  strategy_total?: number;
  strategy_skip?: number;
  strategy_limit?: number;
}

export interface StrategyListResponse {
  items: ImplementedStrategy[];
  total: number;
  skip: number;
  limit: number;
}

export interface AdminStrategyCreatePayload {
  name: string;
  description?: string | null;
  strategy_type?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  visibility?: StrategyVisibility;
  source_request_id?: string | null;
  created_by?: string | null;
  performance_metrics?: {
    winRate?: number | null;
    sharpeRatio?: number | null;
    maxDrawdown?: number | null;
    totalTrades?: number | null;
    profitFactor?: number | null;
  } | null;
  parameters?: Record<string, any> | null;
}

export interface AdminStrategyUpdatePayload {
  name?: string;
  description?: string | null;
  strategy_type?: string | null;
  market?: string | null;
  timeframe?: string | null;
  entry_rules?: string | null;
  exit_rules?: string | null;
  confirmation_rules?: string | null;
  risk_rules?: string | null;
  invalidation_rules?: string | null;
  trade_management_rules?: string | null;
  notes?: string | null;
  visibility?: StrategyVisibility;
  source_request_id?: string | null;
  performance_metrics?: {
    winRate?: number | null;
    sharpeRatio?: number | null;
    maxDrawdown?: number | null;
    totalTrades?: number | null;
    profitFactor?: number | null;
  } | null;
  parameters?: Record<string, any> | null;
}

export interface DeployStrategyRequestPayload {
  strategy_id?: string;
  strategy_name?: string;
  strategy_description?: string;
  publish?: boolean;
  visibility?: StrategyVisibility;
  admin_notes?: string;
}

export const adminApi = {
  getMetrics: async (): Promise<AdminMetrics> =>
    unwrap(await axiosInstance.get("/api/v1/admin/metrics")),

  getUsers: async (skip = 0, limit = 20, search?: string): Promise<PaginatedResponse<User>> =>
    unwrap(await axiosInstance.get("/api/v1/admin/users", { params: { skip, limit, ...(search && { search }) } })),

  createUser: async (payload: any) =>
    unwrap(await axiosInstance.post("/api/v1/admin/users", payload)),

  updateUser: async (userId: string, payload: any) =>
    unwrap(await axiosInstance.put(`/api/v1/admin/users/${userId}`, payload)),

  deleteUser: async (userId: string) =>
    unwrap(await axiosInstance.delete(`/api/v1/admin/users/${userId}`)),

  updateUserStatus: async (userId: string, isActive: boolean) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/status`, { is_active: isActive })),

  updateUserRole: async (userId: string, role: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/role`, { role })),

  getPayments: async (skip = 0, limit = 20, status?: string) =>
    unwrap(await axiosInstance.get("/api/v1/admin/payments", { params: { skip, limit, ...(status && { status }) } })),

  getSubscriptions: async (skip = 0, limit = 20, status?: string) =>
    unwrap(await axiosInstance.get("/api/v1/admin/subscriptions", { params: { skip, limit, ...(status && { status }) } })),

  getCredits: async (skip = 0, limit = 20, search?: string) =>
    unwrap(await axiosInstance.get("/api/v1/admin/credits/ledger", { params: { skip, limit, ...(search && { search }) } })),

  getSupportTickets: async (skip = 0, limit = 20, status?: string) =>
    unwrap(await axiosInstance.get("/api/v1/admin/support-tickets", { params: { skip, limit, ...(status && { status }) } })),

  updateTicketStatus: async (ticketId: string, status: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/support-tickets/${ticketId}`, { status })),

  replyToTicket: async (ticketId: string, message: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/reply`, { message })),

  getOrders: async (
    page = 1,
    page_size = 20,
    status?: string,
    search?: string,
    from_date?: string,
    to_date?: string,
  ) =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/orders", {
        params: { page, page_size, ...(status && { status }), ...(search && { search }), ...(from_date && { from_date }), ...(to_date && { to_date }) },
      }),
    ),

  getOrder: async (orderId: string) =>
    unwrap(await axiosInstance.get(`/api/v1/admin/orders/${orderId}`)),

  updateOrderStatus: async (orderId: string, status: string) =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/orders/${orderId}/status`, { status })),

  getPayment: async (paymentId: string) =>
    unwrap(await axiosInstance.get(`/api/v1/admin/payments/${paymentId}`)),

  refundPayment: async (paymentId: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/payments/${paymentId}/refund`)),

  addCredits: async (userId: string, amount: number, reason: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/credits/add`, { user_id: userId, amount, reason })),

  deductCredits: async (userId: string, amount: number, reason: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/credits/deduct`, { user_id: userId, amount, reason })),

  getStrategies: async (skip = 0, limit = 20, status?: string, search?: string): Promise<StrategyRequestsResponse> =>
    unwrap(await axiosInstance.get("/api/v1/admin/strategy-requests", { params: { skip, limit, ...(status && { status }), ...(search && { search }) } })),

  getStrategyManagementData: async (params?: {
    requestSkip?: number;
    requestLimit?: number;
    requestStatus?: string;
    requestSearch?: string;
    strategySkip?: number;
    strategyLimit?: number;
    strategySearch?: string;
    strategyVisibility?: StrategyVisibility | "";
    strategySource?: "MANUAL" | "REQUESTED" | "";
  }): Promise<StrategyRequestsResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/strategy-requests", {
        params: {
          skip: params?.requestSkip ?? 0,
          limit: params?.requestLimit ?? 20,
          ...(params?.requestStatus ? { status: params.requestStatus } : {}),
          ...(params?.requestSearch ? { search: params.requestSearch } : {}),
          strategy_skip: params?.strategySkip ?? 0,
          strategy_limit: params?.strategyLimit ?? 100,
          ...(params?.strategySearch ? { strategy_search: params.strategySearch } : {}),
          ...(params?.strategyVisibility ? { strategy_visibility: params.strategyVisibility } : {}),
          ...(params?.strategySource ? { strategy_source: params.strategySource } : {}),
        },
      }),
    ),

  getStrategy: async (requestId: string): Promise<StrategyRequest> =>
    unwrap(await axiosInstance.get(`/api/v1/admin/strategy-requests/${requestId}`)),

  updateStrategy: async (requestId: string, payload: Partial<StrategyRequest>): Promise<StrategyRequest> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/strategy-requests/${requestId}`, payload)),

  deployStrategy: async (requestId: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/deploy`)),

  deployStrategyWithPayload: async (requestId: string, payload: DeployStrategyRequestPayload) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/deploy`, payload)),

  publishStrategy: async (requestId: string) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/publish`)),

  publishStrategyWithPayload: async (requestId: string, payload: DeployStrategyRequestPayload) =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/${requestId}/publish`, payload)),

  listAdminStrategies: async (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    visibility?: StrategyVisibility | "";
    source?: "MANUAL" | "REQUESTED" | "";
  }): Promise<StrategyListResponse> =>
    unwrap(
      await axiosInstance.get("/api/v1/admin/strategy-requests/strategies", {
        params: {
          skip: params?.skip ?? 0,
          limit: params?.limit ?? 20,
          ...(params?.search ? { search: params.search } : {}),
          ...(params?.visibility ? { visibility: params.visibility } : {}),
          ...(params?.source ? { source: params.source } : {}),
        },
      }),
    ),

  createAdminStrategy: async (payload: AdminStrategyCreatePayload): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post("/api/v1/admin/strategy-requests/strategies", payload)),

  updateAdminStrategyById: async (strategyId: string, payload: AdminStrategyUpdatePayload): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.patch(`/api/v1/admin/strategy-requests/strategies/${strategyId}`, payload)),

  deleteAdminStrategyById: async (strategyId: string): Promise<{ id: string; released_request_count: number }> =>
    unwrap(await axiosInstance.delete(`/api/v1/admin/strategy-requests/strategies/${strategyId}`)),

  publishAdminStrategyById: async (strategyId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/publish`)),

  unpublishAdminStrategyById: async (strategyId: string): Promise<ImplementedStrategy> =>
    unwrap(await axiosInstance.post(`/api/v1/admin/strategy-requests/strategies/${strategyId}/unpublish`)),
};