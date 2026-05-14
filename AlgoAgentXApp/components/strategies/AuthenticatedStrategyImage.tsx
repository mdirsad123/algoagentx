"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, ExternalLink, ImageIcon, Loader2 } from "lucide-react";
import { getApiAssetUrl } from "@/lib/api-assets";
import { getStoredAccessToken } from "@/lib/axios";

type AuthenticatedStrategyImageProps = {
  src: string;
  alt: string;
  className?: string;
  fileName?: string | null;
  mimeType?: string | null;
  showDownload?: boolean;
  showOpen?: boolean;
  compact?: boolean;
  imageNumber?: number;
  variant?: "card" | "lightbox";
  onPreview?: () => void;
};

function withDownloadFlag(url: string): string {
  if (!url) return url;
  try {
    const parsed = new URL(url, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    parsed.searchParams.set("download", "1");
    return parsed.toString();
  } catch {
    return url.includes("?") ? `${url}&download=1` : `${url}?download=1`;
  }
}

function errorMessageFor(status?: number): string {
  if (status === 401) return "Please refresh/login again to view this image.";
  if (status === 403) return "You do not have access to this image.";
  if (status === 404) return "File not found on server.";
  return "Preview unavailable — download file";
}

export async function fetchProtectedStrategyImageBlob(url: string, download = false): Promise<Blob> {
  const token = getStoredAccessToken();
  const response = await fetch(download ? withDownloadFlag(url) : url, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const error = new Error(errorMessageFor(response.status));
    (error as Error & { status?: number }).status = response.status;
    throw error;
  }

  return response.blob();
}

export function downloadStrategyImageBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function AuthenticatedStrategyImage({
  src,
  alt,
  className,
  fileName,
  showDownload = true,
  showOpen = true,
  compact = false,
  imageNumber,
  variant = "card",
  onPreview,
}: AuthenticatedStrategyImageProps) {
  const resolvedUrl = useMemo(() => getApiAssetUrl(src), [src]);
  const [blobUrl, setBlobUrl] = useState<string>("");
  const [loading, setLoading] = useState(Boolean(resolvedUrl));
  const [error, setError] = useState<string>("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let alive = true;
    let objectUrl = "";

    if (!resolvedUrl) {
      setLoading(false);
      setError("Preview unavailable — download file");
      return;
    }

    setLoading(true);
    setError("");
    setBlobUrl("");

    fetchProtectedStrategyImageBlob(resolvedUrl)
      .then((blob) => {
        if (!alive) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch((err: Error & { status?: number }) => {
        if (!alive) return;
        setError(err.message || errorMessageFor(err.status));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [resolvedUrl]);

  const downloadImage = useCallback(async () => {
    if (!resolvedUrl) return;
    try {
      setDownloading(true);
      const blob = await fetchProtectedStrategyImageBlob(resolvedUrl, true);
      downloadStrategyImageBlob(blob, fileName || alt || "strategy-image");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }, [alt, fileName, resolvedUrl]);

  const openImage = useCallback(() => {
    if (onPreview) {
      onPreview();
      return;
    }
    if (blobUrl) window.open(blobUrl, "_blank", "noopener,noreferrer");
  }, [blobUrl, onPreview]);

  const heightClass = variant === "lightbox" ? "h-[68vh] max-h-[720px]" : compact ? "h-20" : "h-44";
  const cardClass = variant === "lightbox"
    ? "overflow-hidden rounded-2xl border border-white/10 bg-black/20 shadow-2xl"
    : "group overflow-hidden rounded-2xl border border-border/50 bg-card/25 shadow-lg shadow-black/10 transition duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card/35 hover:shadow-xl";

  return (
    <div className={cardClass}>
      <button
        type="button"
        onClick={openImage}
        disabled={!resolvedUrl || variant === "lightbox"}
        className={`relative flex ${heightClass} w-full items-center justify-center overflow-hidden bg-card/35 text-left disabled:cursor-default`}
        aria-label={`Preview ${fileName || alt}`}
      >
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-card/50 text-xs text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span>Loading screenshot...</span>
          </div>
        ) : null}
        {!loading && blobUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={blobUrl} alt={alt} className={`${heightClass} w-full object-contain ${variant === "card" ? "bg-black/20 transition duration-300 group-hover:scale-[1.02]" : "bg-black/30"} ${className || ""}`} />
        ) : null}
        {!loading && !blobUrl ? (
          <div className="flex h-full w-full flex-col items-center justify-center px-4 text-center text-xs text-muted-foreground">
            <ImageIcon className="mb-2 h-6 w-6 text-primary/70" />
            <span>{error || "Preview unavailable — download file"}</span>
          </div>
        ) : null}
        {variant === "card" && imageNumber ? (
          <span className="absolute left-3 top-3 rounded-full border border-white/15 bg-black/45 px-2.5 py-1 text-[11px] font-semibold text-white shadow-lg backdrop-blur-md">
            #{imageNumber}
          </span>
        ) : null}
        {variant === "card" && blobUrl ? (
          <span className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-3 pb-3 pt-8 text-[11px] font-medium text-white opacity-0 transition group-hover:opacity-100">
            Click to preview
          </span>
        ) : null}
      </button>
      {variant === "card" && !compact ? (
        <div className="space-y-3 p-3">
          <div className="flex items-start justify-between gap-3">
            <p className="min-w-0 truncate text-xs font-medium text-foreground" title={fileName || alt}>{fileName || alt}</p>
            {imageNumber ? <span className="shrink-0 rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">Image {imageNumber}</span> : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {showOpen ? (
              <button
                type="button"
                onClick={openImage}
                disabled={!resolvedUrl}
                className="inline-flex items-center gap-1 rounded-lg border border-border/60 bg-card/30 px-2.5 py-1.5 text-[11px] font-semibold text-foreground transition hover:border-primary/40 hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ExternalLink className="h-3.5 w-3.5" /> Open
              </button>
            ) : null}
            {showDownload ? (
              <button
                type="button"
                onClick={downloadImage}
                disabled={!resolvedUrl || downloading}
                className="inline-flex items-center gap-1 rounded-lg border border-border/60 bg-card/30 px-2.5 py-1.5 text-[11px] font-semibold text-foreground transition hover:border-primary/40 hover:bg-primary/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} Download
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
