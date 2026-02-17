import axiosInstance from "../axios";

export interface AdminMetrics {
  users: {
    total: number;
    active: number;
    recent: any[];
  };
  payments: {
    total: number;
    revenue: number;
    recent: any[];
  };
  credits: {
    total: number;
    active_subscriptions: number;
  };
  screener_jobs: {
    recent: any[];
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  user_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_method: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  created_at: string;
  updated_at: string;
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
  updated_at: string;
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  user_email: string;
  credits: number;
  type: string;
  reason: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  user_id: string;
  user_email: string;
  title: string;
  message: string;
  status: string;
  created_at: string;
  updated_at: string;
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
  updated_at: string;
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

export const adminApi = {
  // Dashboard metrics
  getMetrics: async (): Promise<AdminMetrics> => {
    const response = await axiosInstance.get("/api/v1/admin/metrics");
    return response.data;
  },

  // Users management
  getUsers: async (
    skip: number = 0,
    limit: number = 20,
    search?: string
  ): Promise<PaginatedResponse<User>> => {
    const params: any = { skip, limit };
    if (search) params.search = search;
    const response = await axiosInstance.get("/api/v1/admin/users", { params });
    return response.data;
  },

  updateUserStatus: async (userId: string, isActive: boolean): Promise<{ message: string }> => {
    const response = await axiosInstance.put(`/api/v1/admin/users/${userId}/status`, { is_active: isActive });
    return response.data;
  },

  // Payments management
  getPayments: async (
    skip: number = 0,
    limit: number = 20,
    status?: string
  ): Promise<PaginatedResponse<Payment>> => {
    const params: any = { skip, limit };
    if (status) params.status = status;
    const response = await axiosInstance.get("/api/v1/admin/payments", { params });
    return response.data;
  },

  // Subscriptions management
  getSubscriptions: async (
    skip: number = 0,
    limit: number = 20,
    status?: string
  ): Promise<PaginatedResponse<Subscription>> => {
    const params: any = { skip, limit };
    if (status) params.status = status;
    const response = await axiosInstance.get("/api/v1/admin/subscriptions", { params });
    return response.data;
  },

  // Credits management
  getCredits: async (
    skip: number = 0,
    limit: number = 20
  ): Promise<PaginatedResponse<CreditTransaction>> => {
    const params = { skip, limit };
    const response = await axiosInstance.get("/api/v1/admin/credits", { params });
    return response.data;
  },

  // Support tickets management
  getSupportTickets: async (
    skip: number = 0,
    limit: number = 20,
    status?: string
  ): Promise<PaginatedResponse<SupportTicket>> => {
    const params: any = { skip, limit };
    if (status) params.status = status;
    const response = await axiosInstance.get("/api/v1/admin/support-tickets", { params });
    return response.data;
  },

  updateTicketStatus: async (ticketId: string, status: string): Promise<{ message: string }> => {
    const response = await axiosInstance.patch(`/api/v1/admin/support-tickets/${ticketId}`, { status });
    return response.data;
  },

  replyToTicket: async (ticketId: string, message: string): Promise<{ message: string }> => {
    const response = await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/reply`, { message });
    return response.data;
  },

  // Orders management
  getOrders: async (
    page: number = 1,
    page_size: number = 20,
    status?: string,
    search?: string,
    from_date?: string,
    to_date?: string
  ): Promise<PaginatedResponse<Order>> => {
    const params: any = { 
      page, 
      page_size,
      ...(status && { status }),
      ...(search && { search }),
      ...(from_date && { from_date }),
      ...(to_date && { to_date })
    };
    const response = await axiosInstance.get("/api/v1/admin/orders", { params });
    return response.data;
  },

  getOrder: async (orderId: string): Promise<Order & { items: OrderItem[] }> => {
    const response = await axiosInstance.get(`/api/v1/admin/orders/${orderId}`);
    return response.data;
  },

  updateOrderStatus: async (orderId: string, status: string): Promise<{ message: string }> => {
    const response = await axiosInstance.patch(`/api/v1/admin/orders/${orderId}/status`, { status });
    return response.data;
  },

  // Payments management
  getPayment: async (paymentId: string): Promise<Payment> => {
    const response = await axiosInstance.get(`/api/v1/admin/payments/${paymentId}`);
    return response.data;
  },

  refundPayment: async (paymentId: string): Promise<{ message: string }> => {
    const response = await axiosInstance.post(`/api/v1/admin/payments/${paymentId}/refund`);
    return response.data;
  },

  // Credits management
  adjustCredits: async (userId: string, amount: number, reason: string): Promise<{ message: string }> => {
    const response = await axiosInstance.post(`/api/v1/admin/credits/adjust`, {
      user_id: userId,
      amount,
      reason
    });
    return response.data;
  },
};