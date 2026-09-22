const parseTimeout = (value: string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 1000 ? parsed : fallback;
};

export const API_TIMEOUT_MS = parseTimeout(process.env.NEXT_PUBLIC_API_TIMEOUT_MS, 14400000);
export const HEAVY_API_TIMEOUT_MS = parseTimeout(process.env.NEXT_PUBLIC_HEAVY_API_TIMEOUT_MS || process.env.NEXT_PUBLIC_API_TIMEOUT_MS, 14400000);
export const POLLING_API_TIMEOUT_MS = parseTimeout(process.env.NEXT_PUBLIC_POLLING_API_TIMEOUT_MS, 30000);
