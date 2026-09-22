import { getApiBaseUrl } from "./api-base";

export const getApiAssetUrl = (pathOrUrl?: string | null): string => {
  const value = (pathOrUrl || "").trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith("/api/")) return `${getApiBaseUrl()}${value}`;
  return value;
};
