// lib/axios.ts
import axios from "axios";

const apiURL = process.env.NEXT_PUBLIC_API_SERVER;

// Validate API URL configuration
if (!apiURL) {
  if (process.env.NODE_ENV === "development") {
    console.error(
      "[AXIOS CONFIG ERROR] NEXT_PUBLIC_API_SERVER is not defined!\n" +
      "Please add NEXT_PUBLIC_API_SERVER to your .env.local file.\n" +
      "Example: NEXT_PUBLIC_API_SERVER=http://localhost:8000"
    );
  }
}

const axiosInstance = axios.create({
  baseURL: apiURL || "http://localhost:8000", // Fallback for build time
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
    accept: "application/json",
  },
});

// 🔹 Request interceptor: attach token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 🔹 Response interceptor: handle errors
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // No response (CORS / network issue)
    if (!error.response) {
      console.error("[NETWORK ERROR]", error.message);
      return Promise.reject(error);
    }

    // If 401 and detail contains backend message
    if (error.response.status === 401) {
      const detail = error.response.data?.detail;
      console.error("[AUTH ERROR]", detail || "Invalid credentials");
      
      // Pass the backend detail through for UI to display
      error.response.data = {
        ...error.response.data,
        backend_detail: detail
      };
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
