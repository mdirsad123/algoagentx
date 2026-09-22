import axiosInstance from "../axios";

export type ProfileStats = {
  total_backtests: number;
  connected_brokers: number;
  active_subscription?: string | null;
  credit_balance: number;
  admin_console_access?: boolean;
};

export type Profile = {
  id: string;
  email: string;
  role: string;
  full_name?: string | null;
  fullname?: string | null;
  mobile?: string | null;
  company?: string | null;
  created_at?: string | null;
  last_login_at?: string | null;
  account_status?: string | null;
  stats?: ProfileStats;
};

export type AccountSettings = {
  preferences: Record<string, any>;
  notifications: Record<string, any>;
  safety: Record<string, boolean>;
  admin_alerts: Record<string, any>;
};

export const profileSettingsApi = {
  getProfile: async (): Promise<Profile> => {
    const response = await axiosInstance.get("/api/v1/profile/me");
    return response.data;
  },
  updateProfile: async (body: { full_name?: string; mobile?: string; company?: string }): Promise<Profile> => {
    const response = await axiosInstance.patch("/api/v1/profile/me", body);
    return response.data;
  },
  changePassword: async (body: { current_password: string; new_password: string }): Promise<{ message: string }> => {
    const response = await axiosInstance.post("/api/v1/profile/change-password", body);
    return response.data;
  },
  getSettings: async (): Promise<AccountSettings> => {
    const response = await axiosInstance.get("/api/v1/settings/me");
    return response.data;
  },
  updateSettings: async (body: Partial<AccountSettings>): Promise<AccountSettings> => {
    const response = await axiosInstance.patch("/api/v1/settings/me", body);
    return response.data;
  },
};
