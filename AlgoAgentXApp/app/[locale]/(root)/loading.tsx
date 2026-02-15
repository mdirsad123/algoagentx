import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="space-y-6 p-6">
      {/* Page Header Skeleton */}
      <div className="space-y-2">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-5 w-96" />
      </div>

      {/* Stats Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="p-6 border rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </div>
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-3 w-32" />
          </div>
        ))}
      </div>

      {/* Content Cards Skeleton */}
      <div className="space-y-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-6 space-y-4">
            <Skeleton className="h-6 w-40" />
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, j) => (
                <Skeleton key={j} className="h-12 w-full" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
