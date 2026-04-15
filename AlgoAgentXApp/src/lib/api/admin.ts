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
export interface PaginatedResponse<T> { items: T[]; total: number; skip?: number; limit?: number; page?: number; page_size?: number; }
export interface User { id: string; email: string; role: string; is_active: boolean; created_at: string; updated_at?: string; fullname?: string; mobile?: string; plan?: string; credits?: number; }
export interface Payment { id: string; user_id: string; amount: number; currency: string; status: string; payment_method: string; razorpay_order_id?: string; razorpay_payment_id?: string; created_at: string; updated_at?: string; }
export interface Subscription { id: string; user_id: string; plan_id: string; plan_code: string; billing_period: string; price_inr: number; included_credits: number; status: string; start_at: string; end_at: string; created_at: string; updated_at?: string; }
export interface CreditTransaction { id: string; user_id: string; user_email?: string; credits?: number; type: string; reason?: string; created_at: string; }
export interface Order { id: string; user_id: string; order_number: string; status: string; total_amount: number; currency: string; payment_method: string; created_at: string; updated_at?: string; user_email: string; user_name: string; }
export interface OrderItem { id: string; order_id: string; product_type: string; product_id: string; quantity: number; unit_price: number; total_price: number; product_name?: string; product_description?: string; }

export const adminApi = {
  getMetrics: async (): Promise<AdminMetrics> => unwrap(await axiosInstance.get("/api/v1/admin/metrics")),
  getUsers: async (skip:number=0, limit:number=20, search?:string): Promise<PaginatedResponse<User>> => unwrap(await axiosInstance.get("/api/v1/admin/users", { params: { skip, limit, ...(search && { search }) } })),
  createUser: async (payload:any) => unwrap(await axiosInstance.post("/api/v1/admin/users", payload)),
  updateUser: async (userId:string, payload:any) => unwrap(await axiosInstance.put(`/api/v1/admin/users/${userId}`, payload)),
  deleteUser: async (userId:string) => unwrap(await axiosInstance.delete(`/api/v1/admin/users/${userId}`)),
  updateUserStatus: async (userId:string, isActive:boolean) => unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/status`, { is_active: isActive })),
  updateUserRole: async (userId:string, role:string) => unwrap(await axiosInstance.patch(`/api/v1/admin/users/${userId}/role`, { role })),
  getPayments: async (skip:number=0, limit:number=20, status?:string) => unwrap(await axiosInstance.get("/api/v1/admin/payments", { params: { skip, limit, ...(status && { status }) } })),
  getSubscriptions: async (skip:number=0, limit:number=20, status?:string) => unwrap(await axiosInstance.get("/api/v1/admin/subscriptions", { params: { skip, limit, ...(status && { status }) } })),
  getCredits: async (skip:number=0, limit:number=20, search?:string) => unwrap(await axiosInstance.get("/api/v1/admin/credits/ledger", { params: { skip, limit, ...(search && { search }) } })),
  getSupportTickets: async (skip:number=0, limit:number=20, status?:string) => unwrap(await axiosInstance.get("/api/v1/admin/support-tickets", { params: { skip, limit, ...(status && { status }) } })),
  updateTicketStatus: async (ticketId:string, status:string) => unwrap(await axiosInstance.patch(`/api/v1/admin/support-tickets/${ticketId}`, { status })),
  replyToTicket: async (ticketId:string, message:string) => unwrap(await axiosInstance.post(`/api/v1/admin/support-tickets/${ticketId}/reply`, { message })),
  getOrders: async (page:number=1, page_size:number=20, status?:string, search?:string, from_date?:string, to_date?:string) => unwrap(await axiosInstance.get("/api/v1/admin/orders", { params: { page, page_size, ...(status && { status }), ...(search && { search }), ...(from_date && { from_date }), ...(to_date && { to_date }) } })),
  getOrder: async (orderId:string) => unwrap(await axiosInstance.get(`/api/v1/admin/orders/${orderId}`)),
  updateOrderStatus: async (orderId:string, status:string) => unwrap(await axiosInstance.patch(`/api/v1/admin/orders/${orderId}/status`, { status })),
  getPayment: async (paymentId:string) => unwrap(await axiosInstance.get(`/api/v1/admin/payments/${paymentId}`)),
  refundPayment: async (paymentId:string) => unwrap(await axiosInstance.post(`/api/v1/admin/payments/${paymentId}/refund`)),
  addCredits: async (userId:string, amount:number, reason:string) => unwrap(await axiosInstance.post(`/api/v1/admin/credits/add`, { user_id:userId, amount, reason })),
  deductCredits: async (userId:string, amount:number, reason:string) => unwrap(await axiosInstance.post(`/api/v1/admin/credits/deduct`, { user_id:userId, amount, reason })),
};
