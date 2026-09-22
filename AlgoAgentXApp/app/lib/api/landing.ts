import { apiGet } from "@/lib/axios";
import type { SubscriptionPlansGrouped } from "@/lib/api/subscriptions";

export interface LandingStats {
  total_users: number;
  total_backtests: number;
  total_strategies: number;
  connected_brokers: number;
  live_deployments: number;
}

export const landingApi = {
  getStats: async (): Promise<LandingStats> =>
    apiGet<LandingStats>("/api/v1/public/landing-stats", ({ auth: false } as any)),

  getPlans: async (): Promise<SubscriptionPlansGrouped> =>
    apiGet<SubscriptionPlansGrouped>("/api/v1/subscriptions/plans", ({ auth: false } as any)),
};
