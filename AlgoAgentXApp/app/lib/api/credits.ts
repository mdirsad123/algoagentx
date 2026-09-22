import axiosInstance from "../axios";

export interface CreditSummary {
  user_id: string;
  credit_balance: number;
  included_remaining: number;
  plan_name: string;
  next_reset_date?: string;
  total_transactions: number;
  transaction_counts: Record<string, number>;
  last_updated: string;
}

export const creditsApi = {
  // Get credit summary for the user including balance, included credits, plan info, and next reset date
  getCreditSummary: async (): Promise<CreditSummary> => {
    const response = await axiosInstance.get("/api/v1/credits/summary");
    return response.data;
  }
};