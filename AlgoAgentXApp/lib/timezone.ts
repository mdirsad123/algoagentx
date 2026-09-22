export const DISPLAY_TIME_ZONE = "Asia/Kolkata";
export const DISPLAY_TIME_ZONE_LABEL = "IST (UTC+05:30)";

const EXPLICIT_ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Parse API timestamps as UTC instants.
 *
 * AlgoAgentX legacy tables can return UTC values without a timezone suffix
 * (for example 2026-08-28T14:05:00). Browsers otherwise interpret that text
 * as local wall-clock time, which caused the 5h30m mismatch against charts.
 */
export const parseApiDateTime = (value?: string | Date | null): Date | null => {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const raw = String(value).trim();
  if (!raw) return null;
  if (DATE_ONLY.test(raw)) {
    const parsed = new Date(`${raw}T00:00:00Z`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const utcSafe = EXPLICIT_ZONE.test(normalized) ? normalized : `${normalized}Z`;
  const parsed = new Date(utcSafe);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

export const formatDateTimeIST = (
  value?: string | Date | null,
  options: { seconds?: boolean; includeTimeZone?: boolean } = {},
): string => {
  const parsed = parseApiDateTime(value);
  if (!parsed) return "—";
  const parts = new Intl.DateTimeFormat("en-IN", {
    timeZone: DISPLAY_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: options.seconds ? "2-digit" : undefined,
    hour12: true,
  }).format(parsed);
  return options.includeTimeZone === false ? parts : `${parts} IST`;
};

export const formatDateIST = (value?: string | Date | null): string => {
  if (!value) return "—";
  const raw = String(value).trim();
  if (DATE_ONLY.test(raw)) {
    const [year, month, day] = raw.split("-").map(Number);
    const safe = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: DISPLAY_TIME_ZONE,
      year: "numeric",
      month: "short",
      day: "2-digit",
    }).format(safe);
  }
  const parsed = parseApiDateTime(value);
  if (!parsed) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: DISPLAY_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(parsed);
};

export const formatChartDateTimeIST = (value?: string | Date | null): string => {
  const parsed = parseApiDateTime(value);
  if (!parsed) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: DISPLAY_TIME_ZONE,
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(parsed);
};

export const dateKeyIST = (value?: string | Date | null): string => {
  const parsed = parseApiDateTime(value);
  if (!parsed) return "—";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: DISPLAY_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(parsed);
  const get = (type: string) => parts.find((part) => part.type === type)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}`;
};
