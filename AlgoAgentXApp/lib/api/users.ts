import axiosInstance from "../axios";

export interface User {
  id: string;
  email: string;
  role: string;
}

export const userApi = {
  // Get current user information
  getCurrentUser: async (): Promise<User> => {
    const response = await axiosInstance.get("/api/v1/users/me");
    return response.data;
  }
};