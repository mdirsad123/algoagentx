/**
 * Route helper functions for locale-aware navigation
 */

/**
 * Extract locale from pathname
 * @param pathname - The current pathname (e.g., "/en/dashboard", "/dashboard")
 * @returns The locale code (e.g., "en", "hi", "ar", "fr") or null if not found
 */
export function getLocaleFromPathname(pathname: string): string | null {
  if (!pathname || pathname === '/') {
    return null;
  }
  
  // Match locale pattern: /{locale}/ or /{locale} at the end
  const localeMatch = pathname.match(/^\/([a-z]{2,5}(?:-[A-Z]{2})?)(?:\/|$)/);
  return localeMatch ? localeMatch[1] : null;
}

/**
 * Add locale prefix to href if not already present
 * @param pathname - The current pathname to extract locale from
 * @param href - The target href (e.g., "/dashboard", "/notifications")
 * @returns The href with locale prefix (e.g., "/en/dashboard")
 */
export function withLocale(pathname: string, href: string): string {
  // If href already has a locale prefix, return as-is
  if (href.match(/^\/[a-z]{2,5}(?:-[A-Z]{2})?\b/)) {
    return href;
  }
  
  // Extract locale from current pathname
  const locale = getLocaleFromPathname(pathname);
  
  // If no locale found in pathname, default to "en"
  if (!locale) {
    return `/en${href}`;
  }
  
  // Add locale prefix to href
  return `/${locale}${href}`;
}

/**
 * Normalize path by removing locale prefix and trailing slash
 * @param path - The path to normalize
 * @returns The normalized path
 */
export function normalizePath(path: string): string {
  if (!path || path === '/') {
    return '/';
  }
  
  // Remove locale prefix (2-5 chars with optional dash region) from the beginning
  const normalized = path.replace(/^\/[a-z]{2,5}(?:-[A-Z]{2})?\b/, '') || '/';
  
  // Remove trailing slash
  return normalized.replace(/\/$/, '') || '/';
}