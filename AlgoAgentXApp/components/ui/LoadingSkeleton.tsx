import React from "react";
import { cn } from "@/lib/utils";

export function LoadingSkeleton({ className = "" }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-2xl border border-white/10 bg-white/10 backdrop-blur-xl", className)} />;
}

export function PageLoadingSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-6">
      <LoadingSkeleton className="h-28" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => <LoadingSkeleton key={index} className="h-32" />)}
      </div>
      <LoadingSkeleton className="h-96" />
    </div>
  );
}
