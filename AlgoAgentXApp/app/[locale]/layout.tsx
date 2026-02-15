import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "../../public/registry/themes.css";
import { I18nProvider } from "../../components/shared/i18n-provider";
import { cn } from "../../lib/utils";
import { ThemeProvider } from "../../components/theme-provider";
import { ThemeWrapper } from "../../components/theme-wrapper";
import { Toaster } from "../../components/ui/toaster";
import QueryProvider from "../../components/query-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AlgoAgentX - AI Trading Intelligence",
  description: "AI-Powered Trading Intelligence Platform",
};

export default async function RootLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: { locale: string };
}>) {
  const locale = params.locale;
  
  return (
    <html lang={locale} suppressHydrationWarning>
      <body
        className={cn(inter.className, {
        })}
      >
        <QueryProvider>
          <I18nProvider locale={locale}>
            <ThemeProvider
              attribute="class"
              enableSystem
              disableTransitionOnChange
            >
              <ThemeWrapper>{children}</ThemeWrapper>
            </ThemeProvider>
          </I18nProvider>
        </QueryProvider>
        <Toaster />
      </body>
    </html>
  );
}
