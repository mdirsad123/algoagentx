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

// 🔹 Request interceptor: attach token (except for auth endpoints)
axiosInstance.interceptors.request.use(
  (config) => {
    // Check if this is an auth endpoint that should NOT have Authorization header
    const authEndpoints = [
      "/api/v1/auth/login",
      "/api/v1/auth/signup", 
      "/api/v1/auth/refresh"
    ];
    
    const isAuthEndpoint = authEndpoints.some(endpoint => config.url?.includes(endpoint));
    
    if (isAuthEndpoint) {
      // Skip token attachment for auth endpoints
      if (process.env.NODE_ENV === "development") {
        console.log("[AXIOS] auth request - skipping token", config.url);
      }
      return config;
    }
    
    // For non-auth endpoints, attach token if available
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