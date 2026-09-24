export const getApiBaseUrl = (): string => {
  const configured = (process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_SERVER || '').replace(/\/+$/, '');
  if (configured) return configured;

  if (typeof window !== 'undefined') {
    const { hostname, origin } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return 'http://localhost:8000';
    // Production is served behind Nginx, which proxies /api/* to FastAPI:8000.
    // Use the browser origin so Oracle/public deployments do not expose :8000.
    return origin;
  }

  return 'http://localhost:8000';
};

export const getBackendCallbackUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
};
