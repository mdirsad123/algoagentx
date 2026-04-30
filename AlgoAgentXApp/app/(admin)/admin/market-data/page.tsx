"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
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
  AdminMarketDataImportPayload,
  AdminMarketDataJobRecord,
  AdminMarketDataRefreshPayload,
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

function formatInt(value: number) {
  return new Intl.NumberFormat("en-IN").format(value || 0);
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
  const [actionLoading, setActionLoading] = useState(false);

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

  const [actionInstrumentId, setActionInstrumentId] = useState("");
  const [actionTimeframe, setActionTimeframe] = useState("");
  const [actionSource, setActionSource] = useState("admin");
  const [actionUri, setActionUri] = useState("");
  const [actionNote, setActionNote] = useState("");
  const [actionDryRun, setActionDryRun] = useState(false);
  const [actionForce, setActionForce] = useState(false);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    try {
      const response = await adminApi.getMarketDataCatalog();
      setCatalog(response);
    } catch (error: any) {
      toast.error(error?.message || "Failed to load market-data catalog");
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
        toast.error(error?.message || "Failed to load dataset coverage");
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
        toast.error(error?.message || "Failed to load import jobs");
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

  const triggerHook = async (mode: "import" | "upload" | "refresh") => {
    const instrumentId = actionInstrumentId ? Number(actionInstrumentId) : undefined;
    const base: AdminMarketDataImportPayload & AdminMarketDataRefreshPayload = {
      instrument_id: instrumentId,
      timeframe: actionTimeframe || undefined,
      source: actionSource || undefined,
      note: actionNote || undefined,
      force: actionForce,
      metadata: {},
    };

    setActionLoading(true);
    try {
      if (mode === "refresh") {
        await adminApi.triggerMarketDataRefresh(base);
        toast.success("Refresh hook queued");
      } else if (mode === "upload") {
        await adminApi.triggerMarketDataUpload({ ...base, dataset_uri: actionUri || undefined, dry_run: actionDryRun });
        toast.success("Upload hook queued");
      } else {
        await adminApi.triggerMarketDataImport({ ...base, dataset_uri: actionUri || undefined, dry_run: actionDryRun });
        toast.success("Import hook queued");
      }

      await loadJobs(1);
      await loadDatasets(1);
    } catch (error: any) {
      toast.error(error?.message || `Failed to trigger ${mode} hook`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Market Data Management"
        subtitle="Admin control panel for data coverage, freshness monitoring, and import/update hooks."
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
          <h2 className="mb-3 text-sm font-semibold tracking-tight text-foreground">Import / Refresh Hooks</h2>
          <div className="space-y-3">
            <select value={actionInstrumentId} onChange={(event) => setActionInstrumentId(event.target.value)} className={fieldClass}>
              <option value="">All instruments</option>
              {catalog.instruments.map((instrument) => (
                <option key={instrument.id} value={instrument.id}>
                  {instrument.symbol}
                </option>
              ))}
            </select>

            <select value={actionTimeframe} onChange={(event) => setActionTimeframe(event.target.value)} className={fieldClass}>
              <option value="">All timeframes</option>
              {catalog.timeframes.map((timeframe) => (
                <option key={timeframe} value={timeframe}>
                  {timeframe}
                </option>
              ))}
            </select>

            <input value={actionSource} onChange={(event) => setActionSource(event.target.value)} className={fieldClass} placeholder="Source (admin / vendor)" />
            <input value={actionUri} onChange={(event) => setActionUri(event.target.value)} className={fieldClass} placeholder="Dataset URI (optional)" />
            <textarea value={actionNote} onChange={(event) => setActionNote(event.target.value)} className={fieldClass} rows={2} placeholder="Job note (optional)" />

            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={actionDryRun} onChange={(event) => setActionDryRun(event.target.checked)} />
                Dry run
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={actionForce} onChange={(event) => setActionForce(event.target.checked)} />
                Force
              </label>
            </div>

            <div className="grid grid-cols-1 gap-2">
              <Button disabled={actionLoading} onClick={() => void triggerHook("import")} className="rounded-xl bg-primary text-primary-foreground hover:bg-primary/90">
                {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                Trigger Import
              </Button>
              <Button variant="outline" disabled={actionLoading} onClick={() => void triggerHook("upload")} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
                Trigger Upload Hook
              </Button>
              <Button variant="outline" disabled={actionLoading} onClick={() => void triggerHook("refresh")} className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50">
                Trigger Refresh Hook
              </Button>
            </div>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="border border-border/60 bg-card/30 shadow-xl">
        <div className="border-b border-border/50 px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">Dataset Coverage & Freshness</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Showing {datasets.length} of {datasetTotal} datasets • threshold {staleAfterHours}h
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
                  <th className="px-4 py-3">Freshness</th>
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
                    <td className="px-4 py-3">{formatInt(dataset.total_records)}</td>
                    <td className="px-4 py-3">
                      <Badge className={freshnessBadgeClass[dataset.freshness_status]}>
                        {freshnessLabel[dataset.freshness_status]}
                        {typeof dataset.freshness_age_hours === "number" ? ` • ${dataset.freshness_age_hours}h` : ""}
                      </Badge>
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
            <Button
              variant="outline"
              disabled={datasetPage <= 1 || loadingDatasets}
              onClick={() => void loadDatasets(datasetPage - 1)}
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={datasetPage >= datasetTotalPages || loadingDatasets}
              onClick={() => void loadDatasets(datasetPage + 1)}
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
            >
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
            <Button
              variant="outline"
              disabled={jobPage <= 1 || loadingJobs}
              onClick={() => void loadJobs(jobPage - 1)}
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              disabled={jobPage >= jobTotalPages || loadingJobs}
              onClick={() => void loadJobs(jobPage + 1)}
              className="rounded-xl border-border/60 bg-card/30 text-foreground hover:bg-card/50"
            >
              Next
            </Button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
