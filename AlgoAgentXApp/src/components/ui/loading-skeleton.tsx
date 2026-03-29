import * as React from "react"
import { cn } from "@/lib/utils"

interface LoadingSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
}

const LoadingSkeleton = React.forwardRef<HTMLDivElement, LoadingSkeletonProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800",
        className
      )}
      {...props}
    />
  )
)
LoadingSkeleton.displayName = "LoadingSkeleton"

// Common skeleton variants
export const CardSkeleton = ({ className, ...props }: LoadingSkeletonProps) => (
  <LoadingSkeleton className={cn("h-48 w-full", className)} {...props} />
)

export const TableSkeleton = ({ className, ...props }: LoadingSkeletonProps) => (
  <div className={cn("space-y-4", className)} {...props}>
    {[...Array(5)].map((_, i) => (
      <LoadingSkeleton key={i} className="h-16 w-full rounded-lg" />
    ))}
  </div>
)

export const StatsSkeleton = ({ className, ...props }: LoadingSkeletonProps) => (
  <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6", className)} {...props}>
    {[...Array(4)].map((_, i) => (
      <LoadingSkeleton key={i} className="h-32 w-full rounded-xl" />
    ))}
  </div>
)

export const DashboardSkeleton = () => (
  <div className="space-y-6">
    <div className="space-y-2">
      <LoadingSkeleton className="h-8 w-64 rounded" />
      <LoadingSkeleton className="h-4 w-96 rounded" />
    </div>
    
    <StatsSkeleton />
    
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <LoadingSkeleton className="h-96 w-full rounded-xl" />
      <LoadingSkeleton className="h-96 w-full rounded-xl" />
      <LoadingSkeleton className="h-96 w-full rounded-xl" />
    </div>
  </div>
)

export { LoadingSkeleton }