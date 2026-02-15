'use client';

import { I18nProviderClient } from '../../locales/client';
import { NotificationProvider } from '../../contexts/notification-context';
import { UserProvider } from '../../contexts/user-context';

interface I18nProviderProps {
  children: React.ReactNode;
  locale: string;
}

export function I18nProvider({ children, locale }: I18nProviderProps) {
  return (
    <I18nProviderClient locale={locale}>
      <NotificationProvider>
        <UserProvider>
          {children}
        </UserProvider>
      </NotificationProvider>
    </I18nProviderClient>
  );
}
