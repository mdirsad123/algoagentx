const activeStatuses = new Set(["pending", "queued", "running", "started", "retry", "retrying"]);
const failedStatuses = new Set(["failed", "failure", "cancelled", "canceled", "revoked", "terminated", "expired", "timeout", "timed_out"]);

const unwrap = (value: any): any => value?.success === true ? value.data : value;

function resultData(value: any): any {
  if (typeof value === "string") {
    try { value = JSON.parse(value); }
    catch { throw new Error("Sandbox completed with invalid result JSON; check the worker logs."); }
  }
  value = unwrap(value);
  if (!value || typeof value.summary !== "object" || value.summary === null ||
      !Array.isArray(value.trades) || !Array.isArray(value.equity_curve) || !Array.isArray(value.pnl_calendar)) {
    throw new Error("Sandbox completed without valid result data; check the backtest worker logs.");
  }
  return value;
}

export async function pollSandboxJob<T>(
  initial: any,
  fetchJob: (jobId: string) => Promise<any>,
  options: {
    timeoutMs?: number;
    now?: () => number;
    sleep?: (ms: number) => Promise<void>;
    onUpdate?: (job: { jobId: string; status: string; progress: number; message: string }) => void;
  } = {},
): Promise<T> {
  let job = unwrap(initial);
  const jobId = job?.job_id || job?.id;
  const now = options.now || Date.now;
  const sleep = options.sleep || ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
  const deadline = now() + (options.timeoutMs ?? 15 * 60 * 1000);
  let consecutiveErrors = 0;

  for (;;) {
    const status = String(job?.status || "").trim().toLowerCase();
    options.onUpdate?.({
      jobId: String(jobId || ""),
      status,
      progress: Number(job?.progress ?? 0),
      message: String(job?.message || ""),
    });
    if (failedStatuses.has(status)) {
      let details = job?.result_data;
      if (typeof details === "string") {
        try { details = JSON.parse(details); } catch { details = null; }
      }
      throw new Error(`${details?.error || job?.message || `Sandbox job ${status}`} (job ${jobId || "unknown"})`);
    }
    if (status === "completed" || status === "success") return resultData(job.result_data) as T;
    // Support the existing synchronous response shape, but never render a job
    // envelope as successful metrics or manufacture empty result arrays.
    if (!jobId && !status) return resultData(job) as T;
    if (!jobId) throw new Error("Sandbox response is missing its job ID.");
    if (!activeStatuses.has(status)) throw new Error(`Unexpected sandbox job status: ${status || "empty"} (job ${jobId})`);
    if (now() >= deadline) {
      throw new Error(`Browser stopped waiting for Sandbox job ${jobId}. The job was NOT cancelled; check its status before retrying.`);
    }
    await sleep(Math.min(3000, deadline - now()));
    try {
      job = unwrap(await fetchJob(jobId));
      consecutiveErrors = 0;
    } catch (error: any) {
      const httpStatus = error?.response?.status;
      if (httpStatus === 404) throw new Error(`Sandbox job ${jobId} was not found. Check the API/database before retrying.`);
      if ((httpStatus >= 400 && httpStatus < 500 && httpStatus !== 429) || ++consecutiveErrors >= 3) {
        throw new Error(`Unable to poll Sandbox job ${jobId}: ${error?.message || "request failed"}. The job was NOT cancelled.`);
      }
    }
  }
}