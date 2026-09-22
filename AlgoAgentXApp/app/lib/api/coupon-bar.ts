import apiClient, { apiGet } from "@/lib/axios";

export interface CouponBarConfig {
  enabled: boolean;
  message: string;
  code: string;
}

export const couponBarApi = {
  getPublic: () => apiGet<CouponBarConfig>("/api/v1/settings/coupon-bar", ({ auth: false } as any)),
  getAdmin: () => apiGet<CouponBarConfig>("/api/v1/admin/settings/coupon-bar"),
  updateAdmin: async (payload: CouponBarConfig) => {
    const response = await apiClient.put<CouponBarConfig>("/api/v1/admin/settings/coupon-bar", payload);
    return response.data;
  },
};
