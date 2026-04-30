"use client";

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileText,
  Filter,
  Loader2,
  RefreshCcw,
  Search,
  Upload,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import {
  adminApi,
  AdminMarketDataCatalog,
  AdminMarketDataDataset,
  AdminMarketDataDatasetSummary,
  AdminMarketDataImportSummary,
  AdminMarketDataJobRecord,
  MarketDataFreshnessStatus,
} from "@/lib/api/admin";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const fieldClass =
  "w-full rounded-xl border border-border/60 bg-card/25 px-4 py-2.5 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50 focus:ring-2 focus:ring-primary/35";

const freshnessBadgeClass: Record<MarketDataFreshnessStatus, string> = {
  fresh: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  stale: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  no_data: "border-slate-500/30 bg-slate-500/10 text-slate-200",
};

const freshnessLabel: Record<MarketDataFreshnessStatus, string> = {
  fresh: "Fresh",
  warning: "Warning",
  stale: "Stale",
  no_data: "No Data",
};

const timeframeOptions = ["5m", "15m", "1h", "1d"];

type MarketDataTab = "broker" | "csv";

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatInt(value?: number | null) {
  return new Intl.NumberFormat("en-IN").format(value || 0);
}

function getErrorMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;
}

function SummaryCard({ title, summary }: { title: string; summary: AdminMarketDataImportSummary | null }) {
  if (!summary) return null;
  const errors = summary.errors_sample || summary.errors || [];
  const rows = [
    ["Total rows", summary.total_input_rows],
    ["Valid rows", summary.valid_rows],
    ["Invalid rows", summary.invalid_rows],
    ["Duplicate rows", summary.duplicate_rows],
    ["Inserted rows", summary.inserted_rows],
    ["Updated rows", summary.updated_rows],
    ["Skipped rows", summary.skipped_rows],
  ];

  return (
    <div className="mt-4 rounded-2xl border border-border/60 bg-card/25 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <Badge className="border-primary/30 bg-primary/10 text-primary">Import Summary</Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {rows.map(([label, value]) => (
          <div key={label as string} className="rounded-xl border border-border/50 bg-background/20 p-3">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="mt-1 text-lg font-semibold text-foreground">{formatInt(value as number)}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border/50 bg-background/20 p-3 text-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Min Timestamp</p>
          <p className="mt-1 text-foreground">{formatDateTime(summary.min_timestamp)}</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-background/20 p-3 text-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Max / Latest Timestamp</p>
          <p className="mt-1 text-foreground">{formatDateTime(summary.max_timestamp)}</p>
        </div>
      </div>
      {Array.isArray(errors) && errors.length > 0 ? (
        <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          <p className="mb-2 font-semibold">Errors sample</p>
          <pre className="max-h-32 overflow-auto whitespace-pre-wrap">{JSON.stringify(errors.slice(0, 5), null, 2)}</pre>
        </div>
      ) : null}
    </div>
  );
}

export default function AdminMarketDataPage() {
  const [catalog, setCatalog] = useState<AdminMarketDataCatalog>({ instruments: [], timeframes: [] });
  const [datasets, setDatasets] = useState<AdminMarketDataDataset[]>([]);
  const [summary, setSummary] = useState<AdminMarketDataDatasetSummary>({
    total_datasets: 0,
    total_records: 0,
    fresh_count: 0,
    warning_count: 0,
    stale_count: 0,
    no_data_count: 0,
  });
  const [jobs, setJobs] = useState<AdminMarketDataJobRecord[]>([]);

  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [brokerLoading, setBrokerLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [refreshLoadingKey, setRefreshLoadingKey] = useState<string | null>(null);

  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetTotalPages, setDatasetTotalPages] = useState(1);
  const [datasetTotal, setDatasetTotal] = useState(0);

  const [jobPage, setJobPage] = useState(1);
  const [jobTotalPages, setJobTotalPages] = useState(1);
  const [jobTotal, setJobTotal] = useState(0);

  const [search, setSearch] = useState("");
  const [instrumentIdFilter, setInstrumentIdFilter] = useState("");
  const [timeframeFilter, setTimeframeFilter] = useState("");
  const [freshnessFilter, setFreshnessFilter] = useState<"" | MarketDataFreshnessStatus>("");
  const [staleAfterHours, setStaleAfterHours] = useState(24);

  const [jobSearch, setJobSearch] = useState("");
  const [jobTypeFilter, setJobTypeFilter] = useState("");
  const [failedOnly, setFailedOnly] = useState(false);
  const [invalidOnly, setInvalidOnly] = useState(false);

  const [activeTab, setActiveTab] = useState<MarketDataTab>("broker");
  const [provider, setProvider] = useState("MT5");
  const [brokerInstrumentId, setBrokerInstrumentId] = useState("");
  const [brokerSymbol, setBrokerSymbol] = useState("");
  const [instrumentKey, setInstrumentKey] = useState("");
  const [brokerTimeframe, setBrokerTimeframe] = useState("15m");
  const [brokerStartDate, setBrokerStartDate] = useState("");
  const [brokerEndDate, setBrokerEndDate] = useState("");
  const [brokerDryRun, setBrokerDryRun] = useState(true);
  const [brokerForce, setBrokerForce] = useState(false);
  const [brokerSummary, setBrokerSummary] = useState<AdminMarketDataImportSummary | null>(null);

  const [csvInstrumentId, setCsvInstrumentId] = useState("");
  const [csvTimeframe, setCsvTimeframe] = useState("15m");
  const [csvSource, setCsvSource] = useState("CSV");
  const [csvDryRun, setCsvDryRun] = useState(true);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvSummary, setCsvSummary] = useState<AdminMarketDataImportSummary | null>(null);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    try {
      const response = await adminApi.getMarketDataCatalog();
      setCatalog(response);
    } catch (error: any) {
      toast.error(getErrorMessage(error, "Failed to load market-data catalog"));
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  const loadDatasets = useCallback(
    async (nextPage = datasetPage) => {
      setLoadingDatasets(true);
      try {
        const response = await adminApi.getMarketDataDatasets({
          page: nextPage,
          page_size: 20,
          search: search || undefined,
          instrument_id: instrumentIdFilter ? Number(instrumentIdFilter) : undefined,
          timeframe: timeframeFilter || undefined,
          freshness_status: freshnessFilter || undefined,
          stale_after_hours: staleAfterHours,
        });

        setDatasets(Array.isArray(response.items) ? response.items : []);
        setSummary(response.summary);
        setDatasetPage(response.page);
        setDatasetTotalPages(response.total_pages);
        setDatasetTotal(response.total);
      } catch (error: any) {
        toast.error(getErrorMessage(error, "Failed to load dataset coverage"));
      } finally {
        setLoadingDatasets(false);
      }
    },
    [datasetPage, freshnessFilter, instrumentIdFilter, search, staleAfterHours, timeframeFilter],
  );

  const loadJobs = useCallback(
    async (nextPage = jobPage) => {
      setLoadingJobs(true);
      try {
        const response = await adminApi.getMarketDataJobs({
          page: nextPage,
          page_size: 20,
          search: jobSearch || undefined,
          job_type: (jobTypeFilter as any) || undefined,
          failed_only: failedOnly || undefined,
          has_invalid: invalidOnly || undefined,
        });

        setJobs(Array.isArray(response.items) ? response.items : []);
        setJobPage(response.page);
        setJobTotalPages(response.total_pages);
        setJobTotal(response.total);
      } catch (error: any) {
        toast.error(getErrorMessage(error, "Failed to load import jobs"));
      } finally {
        setLoadingJobs(false);
      }
    },
    [failedOnly, invalidOnly, jobPage, jobSearch, jobTypeFilter],
  );

  useEffect(() => {
    void loadCatalog();
    void loadDatasets(1);
    void loadJobs(1);
  }, []);

  const selectedBrokerInstrument = useMemo(
    () => catalog.instruments.find((instrument) => String(instrument.id) === brokerInstrumentId),
    [brokerInstrumentId, catalog.instruments],
  );

  const selectedCsvInstrument = useMemo(
    () => catalog.instruments.find((instrument) => String(instrument.id) === csvInstrumentId),
    [csvInstrumentId, catalog.instruments],
  );

  useEffect(() => {
    if (!selectedBrokerInstrument) return;
    setBrokerSymbol(selectedBrokerInstrument.broker_symbol || selectedBrokerInstrument.symbol || "");
    setInstrumentKey(selectedBrokerInstrument.upstox_instrument_key || "");
  }, [selectedBrokerInstrument]);

  const availableTimeframes = useMemo(() => {
    const merged = [...timeframeOptions, ...(catalog.timeframes || [])];
    return Array.from(new Set(merged.filter(Boolean)));
  }, [catalog.timeframes]);

  const topCards = useMemo(
    () => [
      { label: "Datasets", value: formatInt(summary.total_datasets), icon: <Database className="h-4 w-4" /> },
      { label: "Total Records", value: formatInt(summary.total_records), icon: <CheckCircle2 className="h-4 w-4" /> },
      {
        label: "Fresh / Warning",
        value: `${formatInt(summary.fresh_count)} / ${formatInt(summary.warning_count)}`,
        icon: <Zap className="h-4 w-4" />,
      },
      { label: "Stale / No Data", value: `${formatInt(summary.stale_count)} / ${formatInt(summary.no_data_count)}`, icon: <AlertTriangle className="h-4 w-4" /> },
    ],
    [summary],
  );

  const buildBrokerPayload = (dryRun: boolean) => {
    const instrumentId = Number(brokerInstrumentId);
    if (!instrumentId) throw new Error("Please select an instrument");
    if (!brokerSymbol.trim()) throw new Error("Symbol is required");
    if (!brokerStartDate || !brokerEndDate) throw new Error("Start date and end date are required");
    return {
      provider,
      instrument_id: instrumentId,
      symbol: brokerSymbol.trim(),
      instrument_key: instrumentKey.trim() || undefined,
      timeframe: brokerTimeframe,
      start_date: brokerStartDate,
      end_date: brokerEndDate,
      dry_run: dryRun,
      metadata: { force: brokerForce },
    } as any;
  };

  const runBrokerPreview = async () => {
    setBrokerLoading(true);
    try {
      const response = await adminApi.fetchMarketDataPreview(buildBrokerPayload(true));
      setBrokerSummary(response.summary);
      toast.success("Broker preview completed");
    } catch (error: any) {
      toast.error(getErrorMessage(error, "Broker preview failed"));
    } finally {
      setBrokerLoading(false);
    }
  };

  const runBrokerImport = async () => {
    setBrokerLoading(true);
    try {
      const response = await adminApi.fetchMarketDataImport(buildBrokerPayload(brokerDryRun));
      setBrokerSummary(response.summary);
      toast.success(brokerDryRun ? "Broker dry run completed" : "Candles saved successfully");
      if (!brokerDryRun) {
        await loadDatasets(1);
        await loadJobs(1);
      }
    } catch (error: any) {
      toast.error(getErrorMessage(error, "Broker import failed"));
    } finally {
      setBrokerLoading(false);
    }
  };

  const refreshMissingForDataset = async (dataset: AdminMarketDataDataset) => {
    const rowKey = `${dataset.instrument_id}-${dataset.timeframe}`;
    const selectedInstrument = catalog.instruments.find((instrument) => instrument.id === dataset.instrument_id);
    const symbol = selectedInstrument?.broker_symbol || selectedInstrument?.symbol || dataset.instrument_symbol;

    if (!symbol) {
      toast.error("Unable to refresh: instrument symbol is missing.");
      return;
    }

    const confirmed = window.confirm(
      `Refresh missing ${dataset.instrument_symbol} ${dataset.timeframe} candles using ${provider}? This will start from the latest saved candle with a small overlap buffer.`,
    );
    if (!confirmed) return;

    setRefreshLoadingKey(rowKey);
    try {
      const response = await adminApi.refreshMissingMarketData({
        provider,
        instrument_id: dataset.instrument_id,
        symbol,
        instrument_key:
          provider === "UPSTOX" && selectedInstrument?.upstox_instrument_key
            ? selectedInstrument.upstox_instrument_key
            : provider === "UPSTOX" && selectedBrokerInstrument?.id === dataset.instrument_id
              ? instrumentKey || undefined
              : undefined,
        timeframe: dataset.timeframe,
        end_date: brokerEndDate || undefined,
        dry_run: brokerDryRun,
      });
      setBrokerSummary(response.summary);
      toast.success(brokerDryRun ? "Refresh missing dry run completed" : "Missing candles refreshed");
      await loadDatasets(datasetPage);
    } catch (error: any) {
      toast.error(getErrorMessage(error, "Refresh missing candles failed"));
    } finally {
      setRefreshLoadingKey(null);
    }
  };

  const runCsvUpload = async (dryRun: boolean) => {
    const instrumentId = Number(csvInstrumentId);
    if (!instrumentId) {
      toast.error("Please select an instrument");
      return;
    }
    if (!csvFile) {
      toast.error("Please choose a CSV file");
      return;
    }

    setCsvLoading(true);
    try {
      const response = await adminApi.uploadMarketDataCsv({
        instrument_id: instrumentId,
        timeframe: csvTimeframe,
        source: csvSource || "CSV",
        dry_run: dryRun,
        file: csvFile,
      });
      setCsvSummary(response.summary);
      toast.success(dryRun ? "CSV validation completed" : "CSV candles saved successfully");
      if (!dryRun) {
        await loadDatasets(1);
        await loadJobs(1);
      }
    } catch (error: any) {
      toast.error(getErrorMessage(error, "CSV upload failed"));
    } finally {
      setCsvLoading(false);
    }
  };

  const onCsvFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setCsvFile(event.target.files?.[0] || null);
    setCsvSummary(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Market Data Management"
        subtitle="Admin control panel for data coverage, broker imports, CSV uploads, freshness monitoring, and diagnostics."
        actions={
          <Button
            variant="outline"
            onClick={() => {
              void loadCatalog();
              void loadDatasets(datasetPage);
              void loadJobs(jobPage);
            }}
            className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
          >
            <RefreshCcw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {topCards.map((card) => (
          <GlassCard key={card.label} className="border border-border/60 bg-card/30 p-4 shadow-xl transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{card.label}</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{card.value}</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-card/40 p-2 text-primary">{card.icon}</div>
            </div>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <GlassCard className="xl:col-span-2 border border-border/60 bg-card/30 p-4 shadow-xl">
          <h2 className="mb-3 text-sm font-semibold tracking-tight text-foreground">Dataset Filters</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div className="relative xl:col-span-2">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className={`${fieldClass} pl-9`}
                placeholder="Search symbol, exchange, market, timeframe"
              />
            </div>

            <select value={instrumentIdFilter} onChange={(event) => setInstrumentIdFilter(event.target.value)} className={fieldClass}>
              <option value="">All instruments</option>
              {catalog.instruments.map((instrument) => (
                <option key={instrument.id} value={instrument.id}>
                  {instrument.symbol}
                </option>
              ))}
            </select>

            <select value={timeframeFilter} onChange={(event) => setTimeframeFilter(event.target.value)} className={fieldClass}>
              <option value="">All timeframes</option>
              {catalog.timeframes.map((timeframe) => (
                <option key={timeframe} value={timeframe}>
                  {timeframe}
                </option>
              ))}
            </select>

            <select value={freshnessFilter} onChange={(event) => setFreshnessFilter(event.target.value as "" | MarketDataFreshnessStatus)} className={fieldClass}>
              <option value="">All freshness</option>
              <option value="fresh">Fresh</option>
              <option value="warning">Warning</option>
              <option value="stale">Stale</option>
              <option value="no_data">No Data</option>
            </select>

            <input
              type="number"
              min={1}
              max={720}
              value={staleAfterHours}
              onChange={(event) => setStaleAfterHours(Number(event.target.value) || 24)}
              className={fieldClass}
              placeholder="Stale threshold (hours)"
            />

            <Button onClick={() => void loadDatasets(1)} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
              <Filter className="mr-2 h-4 w-4" />
              Apply
            </Button>
          </div>
        </GlassCard>

        <GlassCard className="border border-border/60 bg-card/30 p-4 shadow-xl">
          <h2 className="mb-3 text-sm font-semibold tracking-tight text-foreground">Import Health</h2>
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border/50 bg-background/20 p-3">
              <p className="text-xs uppercase tracking-wide">Latest datasets</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{formatInt(datasetTotal)}</p>
            </div>
            <div className="rounded-xl border border-border/50 bg-background/20 p-3">
              <p className="text-xs uppercase tracking-wide">Tracked jobs</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{formatInt(jobTotal)}</p>
            </div>
            <p className="text-xs leading-relaxed">Use broker fetch for MT5/Upstox imports or CSV upload as a fallback. Preview/validate first, then save candles.</p>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="border border-border/60 bg-card/30 p-4 shadow-xl">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">Market Data Import Controls</h2>
            <p className="mt-1 text-xs text-muted-foreground">Fetch candles from broker providers or validate and upload CSV files safely.</p>
          </div>
          <div className="grid grid-cols-2 gap-2 rounded-2xl border border-border/60 bg-background/20 p-1">
            <button
              type="button"
              onClick={() => setActiveTab("broker")}
              className={`rounded-xl px-4 py-2 text-sm transition ${activeTab === "broker" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:bg-card/40 hover:text-foreground"}`}
            >
              Fetch from Broker
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("csv")}
              className={`rounded-xl px-4 py-2 text-sm transition ${activeTab === "csv" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:bg-card/40 hover:text-foreground"}`}
            >
              Upload CSV
            </button>
          </div>
        </div>

        {activeTab === "broker" ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <select value={provider} onChange={(event) => setProvider(event.target.value)} className={fieldClass}>
                <option value="MT5">MT5</option>
                <option value="UPSTOX">UPSTOX</option>
                {process.env.NODE_ENV !== "production" ? <option value="MOCK">MOCK</option> : null}
              </select>

              <select value={brokerInstrumentId} onChange={(event) => setBrokerInstrumentId(event.target.value)} className={fieldClass}>
                <option value="">Select instrument</option>
                {catalog.instruments.map((instrument) => (
                  <option key={instrument.id} value={instrument.id}>
                    {instrument.symbol} • {instrument.exchange}
                  </option>
                ))}
              </select>

              <input value={brokerSymbol} onChange={(event) => setBrokerSymbol(event.target.value)} className={fieldClass} placeholder="Symbol e.g. XAUUSD / NIFTY" />
              <input value={instrumentKey} onChange={(event) => setInstrumentKey(event.target.value)} className={fieldClass} placeholder="Upstox instrument key optional" />

              <select value={brokerTimeframe} onChange={(event) => setBrokerTimeframe(event.target.value)} className={fieldClass}>
                {availableTimeframes.map((timeframe) => (
                  <option key={timeframe} value={timeframe}>{timeframe}</option>
                ))}
              </select>

              <input type="date" value={brokerStartDate} onChange={(event) => setBrokerStartDate(event.target.value)} className={fieldClass} />
              <input type="date" value={brokerEndDate} onChange={(event) => setBrokerEndDate(event.target.value)} className={fieldClass} />

              <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border/60 bg-card/25 px-4 py-2.5 text-sm text-foreground">
                <label className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={brokerDryRun} onChange={(event) => setBrokerDryRun(event.target.checked)} />
                  Dry run
                </label>
                <label className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={brokerForce} onChange={(event) => setBrokerForce(event.target.checked)} />
                  Force overwrite/update
                </label>
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button disabled={brokerLoading || loadingCatalog} onClick={() => void runBrokerPreview()} variant="outline" className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
                {brokerLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                Preview Fetch
              </Button>
              <Button disabled={brokerLoading || loadingCatalog} onClick={() => void runBrokerImport()} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                {brokerLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                Fetch & Save Candles
              </Button>
            </div>

            {selectedBrokerInstrument ? (
              <p className="text-xs text-muted-foreground">Selected: {selectedBrokerInstrument.symbol} • {selectedBrokerInstrument.exchange} • {selectedBrokerInstrument.market}</p>
            ) : null}
            <SummaryCard title="Broker Fetch Result" summary={brokerSummary} />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <select value={csvInstrumentId} onChange={(event) => setCsvInstrumentId(event.target.value)} className={fieldClass}>
                <option value="">Select instrument</option>
                {catalog.instruments.map((instrument) => (
                  <option key={instrument.id} value={instrument.id}>
                    {instrument.symbol} • {instrument.exchange}
                  </option>
                ))}
              </select>

              <select value={csvTimeframe} onChange={(event) => setCsvTimeframe(event.target.value)} className={fieldClass}>
                {availableTimeframes.map((timeframe) => (
                  <option key={timeframe} value={timeframe}>{timeframe}</option>
                ))}
              </select>

              <input value={csvSource} onChange={(event) => setCsvSource(event.target.value)} className={fieldClass} placeholder="Source" />

              <label className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-card/25 px-4 py-2.5 text-sm text-foreground">
                <input type="checkbox" checked={csvDryRun} onChange={(event) => setCsvDryRun(event.target.checked)} />
                Dry run
              </label>

              <div className="md:col-span-2 xl:col-span-4">
                <input type="file" accept=".csv,text/csv" onChange={onCsvFileChange} className={fieldClass} />
                <p className="mt-2 text-xs text-muted-foreground">Accepted headers: Date/Open/High/Low/Close/Volume, timestamp/open/high/low/close/volume, or tick_volume.</p>
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button disabled={csvLoading || !csvFile} onClick={() => void runCsvUpload(true)} variant="outline" className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
                {csvLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                Validate CSV
              </Button>
              <Button disabled={csvLoading || !csvFile} onClick={() => void runCsvUpload(false)} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                {csvLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                Upload & Save Candles
              </Button>
            </div>

            {selectedCsvInstrument ? (
              <p className="text-xs text-muted-foreground">Selected: {selectedCsvInstrument.symbol} • {selectedCsvInstrument.exchange} • {selectedCsvInstrument.market}</p>
            ) : null}
            <SummaryCard title="CSV Import Result" summary={csvSummary} />
          </div>
        )}
      </GlassCard>

      <GlassCard className="border border-border/60 bg-card/30 shadow-xl">
        <div className="border-b border-border/50 px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">Dataset Coverage & Freshness</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Showing {datasets.length} of {datasetTotal} datasets • freshness uses market/session rules
          </p>
        </div>

        {loadingDatasets || loadingCatalog ? (
          <div className="flex items-center justify-center p-8 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading datasets...
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">No datasets found for selected filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3">Instrument</th>
                  <th className="px-4 py-3">Timeframe</th>
                  <th className="px-4 py-3">Latest Candle Date</th>
                  <th className="px-4 py-3">Last Candle At</th>
                  <th className="px-4 py-3">Records</th>
                  <th className="px-4 py-3">Missing From</th>
                  <th className="px-4 py-3">Freshness</th>
                  <th className="px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset) => (
                  <tr key={`${dataset.instrument_id}-${dataset.timeframe}`} className="border-b border-border/30 text-foreground/95">
                    <td className="px-4 py-3">
                      <div className="font-medium">{dataset.instrument_symbol}</div>
                      <div className="text-xs text-muted-foreground">{dataset.exchange} • {dataset.market}</div>
                    </td>
                    <td className="px-4 py-3">{dataset.timeframe}</td>
                    <td className="px-4 py-3">{dataset.latest_candle_date || "—"}</td>
                    <td className="px-4 py-3">{formatDateTime(dataset.last_candle_at)}</td>
                    <td className="px-4 py-3">{formatInt(dataset.total_records || dataset.record_count)}</td>
                    <td className="px-4 py-3">{formatDateTime(dataset.missing_from_date)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <Badge className={freshnessBadgeClass[dataset.freshness_status]}>
                          {freshnessLabel[dataset.freshness_status]}
                          {typeof dataset.freshness_age_hours === "number" ? ` • ${dataset.freshness_age_hours}h` : ""}
                        </Badge>
                        {dataset.market_rule ? <span className="text-[11px] text-muted-foreground">{dataset.market_rule}</span> : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="outline"
                        disabled={refreshLoadingKey === `${dataset.instrument_id}-${dataset.timeframe}`}
                        onClick={() => void refreshMissingForDataset(dataset)}
                        className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
                      >
                        {refreshLoadingKey === `${dataset.instrument_id}-${dataset.timeframe}` ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCcw className="mr-2 h-4 w-4" />
                        )}
                        Refresh Missing
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between px-4 py-3 text-xs text-muted-foreground">
          <span>Page {datasetPage} of {datasetTotalPages}</span>
          <div className="flex gap-2">
            <Button variant="outline" disabled={datasetPage <= 1 || loadingDatasets} onClick={() => void loadDatasets(datasetPage - 1)} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
              Previous
            </Button>
            <Button variant="outline" disabled={datasetPage >= datasetTotalPages || loadingDatasets} onClick={() => void loadDatasets(datasetPage + 1)} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
              Next
            </Button>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="border border-border/60 bg-card/30 shadow-xl">
        <div className="border-b border-border/50 px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">Import Failures & Invalid Datasets</h2>
          <p className="mt-1 text-xs text-muted-foreground">Track failed jobs, invalid row counts, and ingestion diagnostics.</p>
        </div>

        <div className="grid grid-cols-1 gap-3 border-b border-border/40 p-4 md:grid-cols-5">
          <input value={jobSearch} onChange={(event) => setJobSearch(event.target.value)} className={fieldClass} placeholder="Search job id / timeframe / source" />
          <select value={jobTypeFilter} onChange={(event) => setJobTypeFilter(event.target.value)} className={fieldClass}>
            <option value="">All job types</option>
            <option value="market_data_import">Import</option>
            <option value="market_data_upload">Upload</option>
            <option value="market_data_refresh">Refresh</option>
            <option value="CSV_UPLOAD">CSV Upload</option>
          </select>
          <label className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-card/25 px-3 py-2 text-sm text-foreground">
            <input type="checkbox" checked={failedOnly} onChange={(event) => setFailedOnly(event.target.checked)} />
            Failed only
          </label>
          <label className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-card/25 px-3 py-2 text-sm text-foreground">
            <input type="checkbox" checked={invalidOnly} onChange={(event) => setInvalidOnly(event.target.checked)} />
            Invalid data only
          </label>
          <Button onClick={() => void loadJobs(1)} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
            <Filter className="mr-2 h-4 w-4" />
            Apply
          </Button>
        </div>

        {loadingJobs ? (
          <div className="flex items-center justify-center p-8 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">No import/refresh job records for selected filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3">Job</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Scope</th>
                  <th className="px-4 py-3">Progress</th>
                  <th className="px-4 py-3">Rows</th>
                  <th className="px-4 py-3">Error</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} className="border-b border-border/30 text-foreground/95">
                    <td className="px-4 py-3">
                      <div className="font-medium">{job.job_id.slice(0, 10)}...</div>
                      <div className="text-xs text-muted-foreground">{formatDateTime(job.created_at)}</div>
                    </td>
                    <td className="px-4 py-3">{job.job_type}</td>
                    <td className="px-4 py-3">
                      <div>{job.instrument_id ? `#${job.instrument_id}` : "All Instruments"}</div>
                      <div className="text-xs text-muted-foreground">{job.timeframe || "All Timeframes"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={job.status === "failed" ? "border-rose-500/30 bg-rose-500/10 text-rose-200" : "border-border/60 bg-card/40 text-foreground"}>
                        {job.status} • {job.progress}%
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div>Imported: {job.imported_rows ?? "—"}</div>
                      <div className="text-xs text-muted-foreground">Invalid: {job.invalid_rows ?? "—"}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{job.error_message || job.message || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between px-4 py-3 text-xs text-muted-foreground">
          <span>Page {jobPage} of {jobTotalPages} • {jobTotal} jobs</span>
          <div className="flex gap-2">
            <Button variant="outline" disabled={jobPage <= 1 || loadingJobs} onClick={() => void loadJobs(jobPage - 1)} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
              Previous
            </Button>
            <Button variant="outline" disabled={jobPage >= jobTotalPages || loadingJobs} onClick={() => void loadJobs(jobPage + 1)} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
              Next
            </Button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
