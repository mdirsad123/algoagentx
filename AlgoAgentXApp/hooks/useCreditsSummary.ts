import { useState, useEffect } from "react";
import { creditsApi, CreditSummary } from "@/lib/api/credits";

export interface UseCreditsSummaryReturn {
  creditsSummary: CreditSummary | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useCreditsSummary = (): UseCreditsSummaryReturn => {
  const [creditsSummary, setCreditsSummary] = useState<CreditSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCreditsSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await creditsApi.getCreditSummary();
      setCreditsSummary(data);
    } catch (err: any) {
      console.error("Failed to fetch credits summary:", err);
      setError(err.message || "Failed to fetch credits summary");
      setCreditsSummary(null);
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    await fetchCreditsSummary();
  };

  useEffect(() => {
    // Fetch credits summary on mount
    fetchCreditsSummary();

    // Set up interval to refresh every 60 seconds
    const interval = setInterval(fetchCreditsSummary, 60000);

    // Clean up interval on unmount
    return () => {
      clearInterval(interval);
    };
  }, []);

  return {
    creditsSummary,
    loading,
    error,
    refresh,
  };
};