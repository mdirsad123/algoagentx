// lib/api/error.ts

/**
 * Unified API error information structure
 */
export interface ApiErrorInfo {
  message: string;
  code?: string;
  status?: number;
  requestId?: string;
  raw?: any;
}

/**
 * Parse API errors consistently across the application
 * @param err The error object (usually from axios)
 * @returns Parsed error information
 */
export function parseApiError(err: unknown): ApiErrorInfo {
  // Handle axios errors
  if (err && typeof err === 'object' && 'response' in err) {
    const axiosError = err as any;
    const response = axiosError.response;
    const headers = response?.headers || {};
    
    // Extract request ID from headers (multiple possible header names)
    const requestId = headers['x-request-id'] || 
                     headers['x-correlation-id'] || 
                     headers['request-id'] ||
                     headers['x-trace-id'] ||
                     headers['trace-id'];

    // Determine error message with priority
    let message = "Something went wrong";
    
    if (response?.data?.detail && typeof response.data.detail === 'string') {
      message = response.data.detail;
    } else if (response?.data?.message && typeof response.data.message === 'string') {
      message = response.data.message;
    } else if (axiosError.message && typeof axiosError.message === 'string') {
      message = axiosError.message;
    }

    // Extract error code if present
    const code = response?.data?.code;

    return {
      message,
      code,
      status: response?.status,
      requestId,
      raw: response?.data
    };
  }

  // Handle non-axios errors
  if (err && typeof err === 'object' && 'message' in err) {
    const genericError = err as any;
    return {
      message: genericError.message || "Something went wrong",
      raw: err
    };
  }

  // Fallback for unknown error types
  return {
    message: "Something went wrong",
    raw: err
  };
}

/**
 * Create a formatted error message with request ID if available
 * @param error Parsed API error
 * @returns Formatted message string
 */
export function formatErrorMessage(error: ApiErrorInfo): string {
  if (!error.requestId) {
    return error.message;
  }
  
  return `${error.message}\nRequest ID: ${error.requestId}`;
}