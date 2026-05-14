"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Download, ImageIcon, Loader2, X } from "lucide-react";
import { getApiAssetUrl } from "@/lib/api-assets";
import {
  AuthenticatedStrategyImage,
  downloadStrategyImageBlob,
  fetchProtectedStrategyImageBlob,
} from "./AuthenticatedStrategyImage";

export type StrategyAttachmentLike = {
  id?: string | null;
  publicUrl?: string | null;
  public_url?: string | null;
  originalName?: string | null;
  original_name?: string | null;
  fileName?: string | null;
  file_name?: string | null;
  mimeType?: string | null;
  mime_type?: string | null;
};

function attachmentUrl(attachment: StrategyAttachmentLike): string {
  return attachment.publicUrl || attachment.public_url || "";
}

function attachmentName(attachment: StrategyAttachmentLike): string {
  return attachment.originalName || attachment.original_name || attachment.fileName || attachment.file_name || "Strategy screenshot";
}

function attachmentMimeType(attachment: StrategyAttachmentLike): string | null {
  return attachment.mimeType || attachment.mime_type || null;
}

function StrategyAttachmentThumb({
  attachment,
  index,
  compact = false,
  onPreview,
}: {
  attachment: StrategyAttachmentLike;
  index: number;
  compact?: boolean;
  onPreview: () => void;
}) {
  const url = attachmentUrl(attachment);
  const name = attachmentName(attachment);

  return (
    <AuthenticatedStrategyImage
      src={url}
      alt={name}
      fileName={name}
      mimeType={attachmentMimeType(attachment)}
      compact={compact}
      showDownload={!compact}
      showOpen={!compact}
      imageNumber={index + 1}
      onPreview={onPreview}
    />
  );
}

function ScreenshotLightbox({
  items,
  selectedIndex,
  onClose,
  onChange,
}: {
  items: StrategyAttachmentLike[];
  selectedIndex: number | null;
  onClose: () => void;
  onChange: (index: number) => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");
  const isOpen = selectedIndex !== null && selectedIndex >= 0 && selectedIndex < items.length;
  const current = isOpen ? items[selectedIndex] : null;
  const currentName = current ? attachmentName(current) : "Strategy screenshot";
  const currentUrl = current ? getApiAssetUrl(attachmentUrl(current)) : "";
  const canGoPrevious = isOpen && items.length > 1;
  const canGoNext = isOpen && items.length > 1;

  const goPrevious = useCallback(() => {
    if (!isOpen || selectedIndex === null) return;
    onChange((selectedIndex - 1 + items.length) % items.length);
  }, [isOpen, items.length, onChange, selectedIndex]);

  const goNext = useCallback(() => {
    if (!isOpen || selectedIndex === null) return;
    onChange((selectedIndex + 1) % items.length);
  }, [isOpen, items.length, onChange, selectedIndex]);

  const downloadCurrent = useCallback(async () => {
    if (!currentUrl) return;
    try {
      setDownloadError("");
      setDownloading(true);
      const blob = await fetchProtectedStrategyImageBlob(currentUrl, true);
      downloadStrategyImageBlob(blob, currentName);
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }, [currentName, currentUrl]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft") goPrevious();
      if (event.key === "ArrowRight") goNext();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [goNext, goPrevious, isOpen, onClose]);

  if (!isOpen || !current) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 p-3 backdrop-blur-2xl sm:p-5" role="dialog" aria-modal="true">
      <div className="absolute inset-0" onClick={onClose} />
      <div className="relative flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#19072f]/95 shadow-2xl shadow-black/50">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-white/5 px-4 py-3 sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/20 text-primary">
              <ImageIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white" title={currentName}>{currentName}</p>
              <p className="text-xs text-white/60">Image {selectedIndex + 1} of {items.length}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={downloadCurrent}
              disabled={downloading || !currentUrl}
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              <span className="hidden sm:inline">Download</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/10 text-white transition hover:bg-white/15"
              aria-label="Close screenshot preview"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="relative p-3 sm:p-5">
          <AuthenticatedStrategyImage
            key={current.id || currentUrl || selectedIndex}
            src={attachmentUrl(current)}
            alt={currentName}
            fileName={currentName}
            mimeType={attachmentMimeType(current)}
            showDownload={false}
            showOpen={false}
            variant="lightbox"
          />
          {downloadError ? <p className="mt-3 text-center text-xs text-rose-200">{downloadError}</p> : null}

          {canGoPrevious ? (
            <button
              type="button"
              onClick={goPrevious}
              className="absolute left-5 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-black/35 text-white shadow-xl backdrop-blur transition hover:bg-black/55"
              aria-label="Previous screenshot"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          ) : null}
          {canGoNext ? (
            <button
              type="button"
              onClick={goNext}
              className="absolute right-5 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-black/35 text-white shadow-xl backdrop-blur transition hover:bg-black/55"
              aria-label="Next screenshot"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function StrategyAttachmentGallery({
  attachments,
  compact = false,
  emptyText = "No screenshots uploaded yet.",
}: {
  attachments?: StrategyAttachmentLike[] | null;
  compact?: boolean;
  emptyText?: string;
}) {
  const items = useMemo(() => attachments || [], [attachments]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (!items.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border/60 bg-card/20 p-6 text-center text-sm text-muted-foreground">
        <ImageIcon className="mx-auto mb-2 h-6 w-6 text-primary/70" />
        {emptyText || "No screenshots uploaded yet."}
      </div>
    );
  }

  return (
    <>
      <div className={compact ? "grid grid-cols-3 gap-2" : "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"}>
        {items.map((attachment, index) => (
          <StrategyAttachmentThumb
            key={attachment.id || `${attachmentName(attachment)}-${index}`}
            attachment={attachment}
            index={index}
            compact={compact}
            onPreview={() => setSelectedIndex(index)}
          />
        ))}
      </div>
      <ScreenshotLightbox items={items} selectedIndex={selectedIndex} onClose={() => setSelectedIndex(null)} onChange={setSelectedIndex} />
    </>
  );
}
