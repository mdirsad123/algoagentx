import { useI18n, useCurrentLocale } from '@/locales/client';

export function useTranslation() {
   const i18n = useI18n();
  const locale = useCurrentLocale();
  const isRTL = locale === 'ar';

  return {  t: i18n as (key: string, params?: Record<string, any>) => string, locale, isRTL };
}
