export function useTranslation() {
  const locale = 'en'; // Default locale
  const isRTL = false;

  const t = (key: string, params?: Record<string, any>) => {
    // Simple translation function - you can expand this with actual translations
    return key;
  };

  return { t, locale, isRTL };
}
