import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import { Toaster } from "sonner";
import { cn } from "../lib/utils";
import { ToastProvider } from "../components/shared/toast";


export const metadata: Metadata = {
  title: "AlgoAgentX - AI Trading Intelligence",
  description: "AI-Powered Trading Intelligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn("font-sans", {})}
      >
        <ToastProvider>
          <Providers>
            {children}
          </Providers>
          <Toaster richColors />
        </ToastProvider>
      </body>
    </html>
  );
}
