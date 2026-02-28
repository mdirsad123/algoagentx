import * as React from "react"
import { cn } from "@/lib/utils"
import { cssCustomProperties } from "@/components/ui/design-tokens"

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  action?: React.ReactNode
  icon?: React.ReactNode
}

const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className, title, description, action, icon, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center space-y-4 py-12 text-center",
          className
        )}
        style={cssCustomProperties as React.CSSProperties}
        {...props}
      >
        {icon && (
          <div className="text-muted-foreground dark:text-dark-text-muted">
            {icon}
          </div>
        )}
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground dark:text-dark-text-primary">
            {title}
          </h3>
          {description && (
            <p className="text-sm text-muted-foreground dark:text-dark-text-secondary max-w-md">
              {description}
            </p>
          )}
        </div>
        {action && (
          <div className="flex gap-2">
            {action}
          </div>
        )}
      </div>
    )
  }
)

EmptyState.displayName = "EmptyState"

export { EmptyState }
