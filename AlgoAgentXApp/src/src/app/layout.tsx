import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "../lib/utils";
import { ToastProvider } from "../components/shared/toast";

const inter = Inter({ subsets: ["latin"] });

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
        className={cn(inter.className, {
        })}
      >
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  );
}
