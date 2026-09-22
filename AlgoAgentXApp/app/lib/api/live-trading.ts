import { getApiBaseUrl } from "@/lib/api-base";
import axiosInstance from "@/lib/axios";
import { HEAVY_API_TIMEOUT_MS } from "@/lib/api-timeouts";
import type {
  BrokerAccount,
  LiveMode,
  BrokerAccountPayload,
  BrokerAccountInfo,
  BrokerMt5Position,
  BrokerSymbol,
  BrokerTestResponse,
  DeploymentPayload,
  LiveDeploymentSummary,
  ManualSignalResponse,
  BrokerStatusResponse,
  BrokerOrderEvent,
  LiveOrder,
  LivePosition,
  LiveSignal,
  LiveTradeLog,
  StrategyCatalogItem,
  StrategyDeployment,
  AdminLiveDeploymentListResponse,
  AdminLiveDeploymentDetail,
  AdminLiveControlAction,
  LiveCandleSnapshot,
  RunStrategyResponse,
  PlatformTradingSettings,
  PlatformTradingSettingsPayload,
  BrokerProvider,
  BrokerProviderPayload,
  LiveSyncStatus,
  LiveReadiness, LiveCompatibilityResult,
  FullDryTestResponse,
  FinalQaResult,
  QaOrderTestResult,
  MarketInstrument,
  MT5AgentStatus,
  MT5AgentRegisterResponse,
  CTraderAccountsResponse,
  BrokerSyncResponse,
  CTraderTradingAccount,
  CTraderDemoOrderRequest,
  CTraderDemoOrderResponse,
  FundedLiveStatus,
  FundedRiskPlanPayload,
  LiveLatencyResponse,
  LiveLatencyTrace,
  LivePipelineHealth,
} from "@/types/live-trading";

type Envelope<T> = { success?: boolean; data?: T; message?: string } | T;

const unwrap = <T>(payload: Envelope<T>): T => {
  if (payload && typeof payload === "object" && "success" in (payload as Record<string, unknown>)) {
    return ((payload as { data?: T }).data ?? null) as T;
  }
  return payload as T;
};

const toArray = <T>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

export const liveTradingApi = {
  async listAvailableBrokerProviders(): Promise<BrokerProvider[]> {
    const response = await axiosInstance.get<Envelope<BrokerProvider[]>>("/api/v1/broker-accounts/providers/available");
    return toArray<BrokerProvider>(unwrap(response.data));
  },

  async adminListBrokerProviders(): Promise<BrokerProvider[]> {
    const response = await axiosInstance.get<Envelope<BrokerProvider[]>>("/api/v1/admin/broker-providers");
    return toArray<BrokerProvider>(unwrap(response.data));
  },

  async adminCreateBrokerProvider(payload: BrokerProviderPayload): Promise<BrokerProvider> {
    const response = await axiosInstance.post<Envelope<BrokerProvider>>("/api/v1/admin/broker-providers", payload);
    return unwrap(response.data);
  },

  async adminUpdateBrokerProvider(id: string, payload: Partial<BrokerProviderPayload>): Promise<BrokerProvider> {
    const response = await axiosInstance.patch<Envelope<BrokerProvider>>(`/api/v1/admin/broker-providers/${id}`, payload);
    return unwrap(response.data);
  },

  async adminEnableBrokerProvider(id: string): Promise<BrokerProvider> {
    const response = await axiosInstance.post<Envelope<BrokerProvider>>(`/api/v1/admin/broker-providers/${id}/enable`);
    return unwrap(response.data);
  },

  async adminDisableBrokerProvider(id: string): Promise<BrokerProvider> {
    const response = await axiosInstance.post<Envelope<BrokerProvider>>(`/api/v1/admin/broker-providers/${id}/disable`);
    return unwrap(response.data);
  },



  async getBrokerRedirectUri(brokerCode: string): Promise<{ broker_code: string; redirect_uri: string }> {
    const response = await axiosInstance.get<Envelope<{ broker_code: string; redirect_uri: string }>>(`/api/v1/broker-accounts/${brokerCode.toLowerCase()}/redirect-uri`);
    return unwrap(response.data);
  },

  async initiateBrokerOAuth(brokerCode: string, brokerAccountId: string, redirectAfter = "/brokers"): Promise<{ auth_url: string; state: string; broker_account_id?: string | null }> {
    const response = await axiosInstance.post<Envelope<{ auth_url: string; state: string; broker_account_id?: string | null }>>(
      `/api/v1/broker-accounts/${brokerCode.toLowerCase()}/oauth/initiate`,
      { broker_account_id: brokerAccountId, redirect_after: redirectAfter },
      { params: { redirect_after: redirectAfter }, withCredentials: brokerCode.toUpperCase() === "CTRADER" || brokerCode.toUpperCase() === "CTRADER_API" }
    );
    return unwrap(response.data);
  },

  async connectCtraderOAuth(payload: {
    broker_account_id?: string | null;
    account_label: string;
    client_id: string;
    client_secret: string;
    redirect_uri: string;
    redirect_after?: string;
  }): Promise<{ auth_url: string; state: string; broker_account_id: string; redirect_uri: string }> {
    const response = await axiosInstance.post<Envelope<{ auth_url: string; state: string; broker_account_id: string; redirect_uri: string }>>(
      "/api/v1/broker-accounts/ctrader/connect",
      payload,
      { withCredentials: true }
    );
    return unwrap(response.data);
  },

  async createUpstoxBrokerAccount(payload: { account_label: string; client_id: string; client_secret: string; redirect_uri: string; redirect_after?: string }): Promise<BrokerAccount> {
    const response = await axiosInstance.post<Envelope<BrokerAccount>>("/api/v1/broker-accounts/upstox", payload);
    return unwrap(response.data);
  },

  async getUpstoxConnectUrl(redirectAfter = "/brokers"): Promise<{ auth_url: string; state: string; broker_account_id?: string | null }> {
    const response = await axiosInstance.get<Envelope<{ auth_url: string; state: string; broker_account_id?: string | null }>>("/api/v1/broker-accounts/upstox/connect-url", {
      params: { redirect_after: redirectAfter },
    });
    return unwrap(response.data);
  },

  async getUpstoxAccountConnectUrl(accountId: string, redirectAfter = "/brokers"): Promise<{ auth_url: string; state: string; broker_account_id?: string | null }> {
    const response = await axiosInstance.get<Envelope<{ auth_url: string; state: string; broker_account_id?: string | null }>>(`/api/v1/broker-accounts/${accountId}/upstox/connect-url`, {
      params: { redirect_after: redirectAfter },
    });
    return unwrap(response.data);
  },


  getMt5AgentDownloadUrl(): string {
    return `${getApiBaseUrl()}/api/v1/mt5-agent/download`;
  },


  async generateMt5AgentToken(brokerAccountId: string, tradingMode: LiveMode = "DEMO"): Promise<MT5AgentRegisterResponse> {
    const response = await axiosInstance.post<Envelope<MT5AgentRegisterResponse>>("/api/v1/mt5-agent/register", { broker_account_id: brokerAccountId, trading_mode: tradingMode });
    return unwrap(response.data);
  },

  async getMt5AgentStatus(brokerAccountId: string): Promise<MT5AgentStatus | null> {
    const response = await axiosInstance.get<Envelope<MT5AgentStatus | null>>(`/api/v1/mt5-agent/broker-account/${brokerAccountId}/status`);
    return unwrap(response.data);
  },

  async listBrokerAccounts(): Promise<BrokerAccount[]> {
    const response = await axiosInstance.get<Envelope<BrokerAccount[]>>("/api/v1/broker-accounts");
    return toArray<BrokerAccount>(unwrap(response.data));
  },

  async getBrokerAccount(id: string): Promise<BrokerAccount> {
    const response = await axiosInstance.get<Envelope<BrokerAccount>>(`/api/v1/broker-accounts/${id}`);
    return unwrap(response.data);
  },

  async createBrokerAccount(payload: BrokerAccountPayload): Promise<BrokerAccount> {
    const response = await axiosInstance.post<Envelope<BrokerAccount>>("/api/v1/broker-accounts", payload);
    return unwrap(response.data);
  },

  async updateBrokerAccount(id: string, payload: Partial<BrokerAccountPayload>): Promise<BrokerAccount> {
    const response = await axiosInstance.patch<Envelope<BrokerAccount>>(`/api/v1/broker-accounts/${id}`, payload);
    return unwrap(response.data);
  },

  async deleteBrokerAccount(id: string, force = false): Promise<void> {
    await axiosInstance.delete(`/api/v1/broker-accounts/${id}`, { params: { force } });
  },

  async testBrokerConnection(id: string): Promise<BrokerTestResponse> {
    const response = await axiosInstance.post<Envelope<BrokerTestResponse>>(`/api/v1/broker-accounts/${id}/test`);
    return unwrap(response.data);
  },


  async getCtraderAccounts(id: string): Promise<CTraderAccountsResponse> {
    const response = await axiosInstance.get<Envelope<CTraderAccountsResponse>>(`/api/v1/broker-accounts/${id}/ctrader/accounts`);
    return unwrap(response.data);
  },

  async selectCtraderAccount(id: string, accountId: string): Promise<{ broker_account: BrokerAccount; selected_account: CTraderTradingAccount }> {
    const response = await axiosInstance.post<Envelope<{ broker_account: BrokerAccount; selected_account: CTraderTradingAccount }>>(`/api/v1/broker-accounts/${id}/ctrader/select-account`, { account_id: accountId });
    return unwrap(response.data);
  },

  async syncBrokerAccount(id: string): Promise<BrokerSyncResponse> {
    const response = await axiosInstance.post<Envelope<BrokerSyncResponse>>(`/api/v1/broker-accounts/${id}/sync`, undefined, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },


  async placeCtraderTestOrder(id: string, payload: CTraderDemoOrderRequest): Promise<CTraderDemoOrderResponse> {
    const response = await axiosInstance.post<Envelope<CTraderDemoOrderResponse>>(`/api/v1/broker-accounts/${id}/ctrader/test-order`, payload, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async getBrokerAccountInfo(id: string): Promise<BrokerAccountInfo> {
    const response = await axiosInstance.get<Envelope<BrokerAccountInfo>>(`/api/v1/broker-accounts/${id}/account-info`);
    return unwrap(response.data);
  },

  async getBrokerPositions(id: string): Promise<BrokerMt5Position[]> {
    const response = await axiosInstance.get<Envelope<BrokerMt5Position[]>>(`/api/v1/broker-accounts/${id}/positions`);
    return toArray<BrokerMt5Position>(unwrap(response.data));
  },

  async listBrokerSymbols(id: string, query = "", limit = 200): Promise<BrokerSymbol[]> {
    const response = await axiosInstance.get<Envelope<BrokerSymbol[]>>(`/api/v1/broker-accounts/${id}/symbols`, { params: { query, limit } });
    return toArray<BrokerSymbol>(unwrap(response.data));
  },


  async listMarketInstruments(search = ""): Promise<MarketInstrument[]> {
    const response = await axiosInstance.get<Envelope<MarketInstrument[]>>("/api/v1/market-master/instruments", {
      params: search ? { search } : undefined,
    });
    return toArray<MarketInstrument>(unwrap(response.data));
  },

  async listStrategies(): Promise<StrategyCatalogItem[]> {
    const response = await axiosInstance.get<Envelope<StrategyCatalogItem[]>>("/api/v1/strategies");
    const rows = toArray<StrategyCatalogItem>(unwrap(response.data));
    return rows.filter((item) => item.status === "PUBLISHED" || item.visibility === "PUBLIC");
  },


  async getLiveAccessStatus(): Promise<{ allowed: boolean; requires_subscription: boolean; code?: string | null; message?: string; recommended_coupon?: string | null; subscription?: Record<string, unknown> | null; funded_live?: { allowed: boolean; requires_subscription: boolean; code?: string | null; message?: string; subscription?: Record<string, unknown> | null } }> {
    const response = await axiosInstance.get<Envelope<{ allowed: boolean; requires_subscription: boolean; code?: string | null; message?: string; recommended_coupon?: string | null; subscription?: Record<string, unknown> | null; funded_live?: { allowed: boolean; requires_subscription: boolean; code?: string | null; message?: string; subscription?: Record<string, unknown> | null } }>>("/api/v1/live/deployments/access-status");
    return unwrap(response.data);
  },

  async listDeployments(): Promise<StrategyDeployment[]> {
    const response = await axiosInstance.get<Envelope<StrategyDeployment[]>>("/api/v1/live/deployments");
    return toArray<StrategyDeployment>(unwrap(response.data));
  },

  async createDeployment(payload: DeploymentPayload): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>("/api/v1/live/deployments", payload);
    return unwrap(response.data);
  },

  async deleteDeployment(id: string): Promise<void> {
    await axiosInstance.delete(`/api/v1/live/deployments/${id}`);
  },

  async getDeployment(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.get<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}`);
    return unwrap(response.data);
  },

  async getDeploymentSummary(id: string, options?: { refreshBroker?: boolean }): Promise<LiveDeploymentSummary> {
    const response = await axiosInstance.get<Envelope<LiveDeploymentSummary>>(`/api/v1/live/deployments/${id}/summary`, {
      params: { refresh_broker: options?.refreshBroker ?? true },
    });
    return unwrap(response.data);
  },

  async getDeploymentReadiness(id: string): Promise<LiveReadiness> {
    const response = await axiosInstance.get<Envelope<LiveReadiness>>(`/api/v1/live/deployments/${id}/readiness`);
    return unwrap(response.data);
  },

  async getDeploymentLatency(id: string, limit = 50): Promise<LiveLatencyResponse> {
    const response = await axiosInstance.get<Envelope<LiveLatencyResponse>>(`/api/v1/live/deployments/${id}/latency`, { params: { limit } });
    return unwrap(response.data);
  },

  async getDeploymentLatestLatency(id: string): Promise<LiveLatencyTrace | null> {
    const response = await axiosInstance.get<Envelope<LiveLatencyTrace | null>>(`/api/v1/live/deployments/${id}/latency/latest`);
    return unwrap(response.data);
  },

  async getDeploymentPipelineHealth(id: string): Promise<LivePipelineHealth> {
    const response = await axiosInstance.get<Envelope<LivePipelineHealth>>(`/api/v1/live/deployments/${id}/pipeline-health`);
    return unwrap(response.data);
  },

  async getFundedStatus(id: string): Promise<FundedLiveStatus | { account_policy_type: "STANDARD"; funded: null }> {
    const response = await axiosInstance.get<Envelope<FundedLiveStatus | { account_policy_type: "STANDARD"; funded: null }>>(
      `/api/v1/live/deployments/${id}/funded-status`
    );
    return unwrap(response.data);
  },

  async refreshFundedStatus(id: string): Promise<{ funded: FundedLiveStatus; decision?: Record<string, unknown>; broker_sync?: Record<string, unknown> }> {
    const response = await axiosInstance.post<Envelope<{ funded: FundedLiveStatus; decision?: Record<string, unknown>; broker_sync?: Record<string, unknown> }>>(
      `/api/v1/live/deployments/${id}/funded-refresh`,
      undefined,
      { timeout: HEAVY_API_TIMEOUT_MS }
    );
    return unwrap(response.data);
  },

  async updateFundedRiskPlan(id: string, payload: FundedRiskPlanPayload): Promise<FundedLiveStatus> {
    const response = await axiosInstance.patch<Envelope<FundedLiveStatus>>(
      `/api/v1/live/deployments/${id}/funded-risk-plan`,
      payload
    );
    return unwrap(response.data);
  },

  async advanceFundedPhase(
    id: string,
    payload: { broker_account_id?: string | null; confirm: boolean }
  ): Promise<FundedLiveStatus> {
    const response = await axiosInstance.post<Envelope<FundedLiveStatus>>(
      `/api/v1/live/deployments/${id}/funded/advance-phase`,
      payload,
      { timeout: HEAVY_API_TIMEOUT_MS }
    );
    return unwrap(response.data);
  },

  async runCompatibilityCheck(id: string): Promise<LiveCompatibilityResult> {
    const response = await axiosInstance.post<Envelope<LiveCompatibilityResult>>(`/api/v1/live/deployments/${id}/compatibility-check`, undefined, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async createDeploymentManualSignal(id: string, payload: { signal_type?: string; signal?: string; price: number; reason?: string | null }): Promise<ManualSignalResponse> {
    const response = await axiosInstance.post<Envelope<ManualSignalResponse>>(`/api/v1/live/deployments/${id}/manual-signal`, payload);
    return unwrap(response.data);
  },


  async refreshDeploymentCandles(id: string, count = 100): Promise<LiveCandleSnapshot> {
    const response = await axiosInstance.post<Envelope<LiveCandleSnapshot>>(`/api/v1/live/deployments/${id}/refresh-candles`, null, { params: { count } });
    return unwrap(response.data);
  },

  async getDeploymentCandles(id: string, limit = 300): Promise<LiveCandleSnapshot> {
    const response = await axiosInstance.get<Envelope<LiveCandleSnapshot>>(`/api/v1/live/deployments/${id}/candles`, { params: { limit } });
    return unwrap(response.data);
  },

  async runStrategyOnce(id: string, execute = true): Promise<RunStrategyResponse> {
    const response = await axiosInstance.post<Envelope<RunStrategyResponse>>(`/api/v1/live/deployments/${id}/run-strategy-once`, { execute }, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async runFullDryTest(id: string): Promise<FullDryTestResponse> {
    const response = await axiosInstance.post<Envelope<FullDryTestResponse>>(`/api/v1/live/deployments/${id}/run-full-dry-test`, undefined, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async getFinalQa(id: string): Promise<FinalQaResult> {
    const response = await axiosInstance.get<Envelope<FinalQaResult>>(`/api/v1/live/deployments/${id}/final-qa`, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async runPaperOrderTest(id: string, side = "BUY"): Promise<QaOrderTestResult> {
    const response = await axiosInstance.post<Envelope<QaOrderTestResult>>(`/api/v1/live/deployments/${id}/test-paper-order`, { side }, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async runDemoMicroOrderTest(id: string, payload: { side?: string; confirm_demo_micro_order: boolean }): Promise<QaOrderTestResult> {
    const response = await axiosInstance.post<Envelope<QaOrderTestResult>>(`/api/v1/live/deployments/${id}/test-demo-micro-order`, payload, { timeout: HEAVY_API_TIMEOUT_MS });
    return unwrap(response.data);
  },

  async enableAutoRunner(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/auto-runner/enable`);
    return unwrap(response.data);
  },

  async disableAutoRunner(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/auto-runner/disable`);
    return unwrap(response.data);
  },

  async runAutoRunnerNow(id: string): Promise<Record<string, unknown>> {
    const response = await axiosInstance.post<Envelope<Record<string, unknown>>>(`/api/v1/live/deployments/${id}/auto-runner/run-now`);
    return unwrap(response.data);
  },

  async adminRunnerTick(): Promise<Record<string, unknown>> {
    const response = await axiosInstance.post<Envelope<Record<string, unknown>>>("/api/v1/live/runner/tick");
    return unwrap(response.data);
  },

  async getDeploymentBrokerStatus(id: string): Promise<BrokerStatusResponse> {
    const response = await axiosInstance.get<Envelope<BrokerStatusResponse>>(`/api/v1/live/deployments/${id}/broker-status`);
    return unwrap(response.data);
  },

  async syncDeploymentBroker(id: string): Promise<Record<string, unknown>> {
    const response = await axiosInstance.post<Envelope<Record<string, unknown>>>(`/api/v1/live/deployments/${id}/sync-broker`);
    return unwrap(response.data);
  },

  async processPaperPositions(id: string): Promise<Record<string, unknown>> {
    const response = await axiosInstance.post<Envelope<Record<string, unknown>>>(`/api/v1/live/deployments/${id}/process-paper-positions`);
    return unwrap(response.data);
  },

  async listDeploymentPositionEvents(id: string, limit = 100): Promise<LiveTradeLog[]> {
    const response = await axiosInstance.get<Envelope<LiveTradeLog[]>>(`/api/v1/live/deployments/${id}/position-events`, { params: { limit } });
    return toArray<LiveTradeLog>(unwrap(response.data));
  },

  async enableLiveSync(id: string, interval_seconds = 10): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/live-sync/enable`, { interval_seconds });
    return unwrap(response.data);
  },

  async disableLiveSync(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/live-sync/disable`);
    return unwrap(response.data);
  },

  async updateLiveSyncSettings(id: string, interval_seconds: number): Promise<StrategyDeployment> {
    const response = await axiosInstance.patch<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/live-sync/settings`, { interval_seconds });
    return unwrap(response.data);
  },

  async getLiveSyncStatus(id: string): Promise<LiveSyncStatus> {
    const response = await axiosInstance.get<Envelope<LiveSyncStatus>>(`/api/v1/live/deployments/${id}/live-sync/status`);
    return unwrap(response.data);
  },

  async listDeploymentBrokerEvents(id: string, limit = 50): Promise<BrokerOrderEvent[]> {
    const response = await axiosInstance.get<Envelope<BrokerOrderEvent[]>>(`/api/v1/live/deployments/${id}/broker-events`, { params: { limit } });
    return toArray<BrokerOrderEvent>(unwrap(response.data));
  },

  async adminSyncDeploymentBroker(id: string): Promise<{ sync: Record<string, unknown>; detail: AdminLiveDeploymentDetail }> {
    const response = await axiosInstance.post<Envelope<{ sync: Record<string, unknown>; detail: AdminLiveDeploymentDetail }>>(`/api/v1/admin/live/deployments/${id}/sync-broker`);
    return unwrap(response.data);
  },

  async previewLiveOrder(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await axiosInstance.post<Envelope<Record<string, unknown>>>("/api/v1/live-trading/order-preview", payload);
    return unwrap(response.data);
  },

  async updateDeployment(id: string, payload: Partial<DeploymentPayload>): Promise<StrategyDeployment> {
    const response = await axiosInstance.patch<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}`, payload);
    return unwrap(response.data);
  },

  async startDeployment(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/start`);
    return unwrap(response.data);
  },

  async pauseDeployment(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/pause`);
    return unwrap(response.data);
  },

  async stopDeployment(id: string): Promise<StrategyDeployment> {
    const response = await axiosInstance.post<Envelope<StrategyDeployment>>(`/api/v1/live/deployments/${id}/stop`);
    return unwrap(response.data);
  },

  async listSignals(deploymentId?: string): Promise<LiveSignal[]> {
    const response = await axiosInstance.get<Envelope<LiveSignal[]>>("/api/v1/live/signals", {
      params: deploymentId ? { deployment_id: deploymentId } : undefined,
    });
    return toArray<LiveSignal>(unwrap(response.data));
  },

  async createManualSignal(payload: {
    deployment_id: string;
    signal_type: string;
    side?: string | null;
    price?: number | null;
    reason?: string | null;
  }): Promise<LiveSignal> {
    const response = await axiosInstance.post<Envelope<LiveSignal>>("/api/v1/live/signals/manual", payload);
    return unwrap(response.data);
  },

  async listOrders(deploymentId?: string): Promise<LiveOrder[]> {
    const response = await axiosInstance.get<Envelope<LiveOrder[]>>("/api/v1/live/orders", {
      params: deploymentId ? { deployment_id: deploymentId } : undefined,
    });
    return toArray<LiveOrder>(unwrap(response.data));
  },

  async listPositions(deploymentId?: string): Promise<LivePosition[]> {
    const response = await axiosInstance.get<Envelope<LivePosition[]>>("/api/v1/live/positions", {
      params: deploymentId ? { deployment_id: deploymentId } : undefined,
    });
    return toArray<LivePosition>(unwrap(response.data));
  },

  async listOpenPositions(): Promise<LivePosition[]> {
    const response = await axiosInstance.get<Envelope<LivePosition[]>>("/api/v1/live/positions/open");
    return toArray<LivePosition>(unwrap(response.data));
  },

  async listLogs(deploymentId?: string): Promise<LiveTradeLog[]> {
    const response = await axiosInstance.get<Envelope<LiveTradeLog[]>>("/api/v1/live/logs", {
      params: deploymentId ? { deployment_id: deploymentId } : undefined,
    });
    return toArray<LiveTradeLog>(unwrap(response.data));
  },

  async adminListLiveDeployments(params?: Record<string, string>): Promise<AdminLiveDeploymentListResponse> {
    const response = await axiosInstance.get<Envelope<AdminLiveDeploymentListResponse>>("/api/v1/admin/live/deployments", { params });
    return unwrap(response.data);
  },

  async adminGetLiveDeployment(id: string): Promise<AdminLiveDeploymentDetail> {
    const response = await axiosInstance.get<Envelope<AdminLiveDeploymentDetail>>(`/api/v1/admin/live/deployments/${id}`);
    return unwrap(response.data);
  },

  async adminRunStrategyOnce(id: string, execute = true): Promise<{ runner: RunStrategyResponse; detail: AdminLiveDeploymentDetail }> {
    const response = await axiosInstance.post<Envelope<{ runner: RunStrategyResponse; detail: AdminLiveDeploymentDetail }>>(`/api/v1/admin/live/deployments/${id}/run-strategy-once`, { execute });
    return unwrap(response.data);
  },

  async adminControlDeployment(id: string, action: AdminLiveControlAction, reason?: string): Promise<AdminLiveDeploymentDetail> {
    const response = await axiosInstance.post<Envelope<AdminLiveDeploymentDetail>>(`/api/v1/admin/live/deployments/${id}/${action}`, { reason });
    return unwrap(response.data);
  },


  async adminEnableLiveSync(id: string, interval_seconds = 10): Promise<AdminLiveDeploymentDetail> {
    const response = await axiosInstance.post<Envelope<AdminLiveDeploymentDetail>>(`/api/v1/admin/live/deployments/${id}/live-sync/enable`, { interval_seconds });
    return unwrap(response.data);
  },

  async adminDisableLiveSync(id: string): Promise<AdminLiveDeploymentDetail> {
    const response = await axiosInstance.post<Envelope<AdminLiveDeploymentDetail>>(`/api/v1/admin/live/deployments/${id}/live-sync/disable`);
    return unwrap(response.data);
  },

  async adminUpdateLiveSyncSettings(id: string, interval_seconds: number): Promise<AdminLiveDeploymentDetail> {
    const response = await axiosInstance.patch<Envelope<AdminLiveDeploymentDetail>>(`/api/v1/admin/live/deployments/${id}/live-sync/settings`, { interval_seconds });
    return unwrap(response.data);
  },







  async getLiveSettings(): Promise<PlatformTradingSettings> {
    const response = await axiosInstance.get<Envelope<PlatformTradingSettings>>("/api/v1/admin/live-settings");
    return unwrap(response.data);
  },

  async updateLiveSettings(payload: PlatformTradingSettingsPayload): Promise<PlatformTradingSettings> {
    const response = await axiosInstance.patch<Envelope<PlatformTradingSettings>>("/api/v1/admin/live-settings", payload);
    return unwrap(response.data);
  },

  async setKillSwitch(enabled: boolean): Promise<PlatformTradingSettings> {
    const response = await axiosInstance.post<Envelope<PlatformTradingSettings>>(`/api/v1/admin/live-settings/kill-switch/${enabled ? "on" : "off"}`);
    return unwrap(response.data);
  },

  async forceStopAllLive(): Promise<{ affected: number }> {
    const response = await axiosInstance.post<Envelope<{ affected: number }>>("/api/v1/admin/live-trading/force-stop-all");
    return unwrap(response.data);
  },

  async pauseAllDemoLive(): Promise<{ affected: number }> {
    const response = await axiosInstance.post<Envelope<{ affected: number }>>("/api/v1/admin/live-trading/pause-all-demo");
    return unwrap(response.data);
  },

};
