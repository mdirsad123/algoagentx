import axiosInstance from "../axios";

export interface User {
  id: string;
  email: string;
  role: string;
  full_name?: string;
  fullname?: string;
  created_at?: string;
}

export const userApi = {
  getCurrentUser: async (): Promise<User> => {
    const response = await axiosInstance.get("/api/v1/users/me");
    return response.data;
  },
};
