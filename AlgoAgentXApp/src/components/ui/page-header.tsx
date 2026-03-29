import * as React from "react"
import { cn } from "@/lib/utils"
import { cssCustomProperties } from "./design-tokens"

interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

const PageHeader = React.forwardRef<HTMLDivElement, PageHeaderProps>(
  ({ className, title, subtitle, actions, ...props }, ref) => (
    <div 
      ref={ref} 
      className={cn("space-y-4", className)} 
      style={cssCustomProperties as React.CSSProperties}
      {...props}
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-dark-text-primary">{title}</h1>
          {subtitle && (
            <p className="text-neutral-600 dark:text-dark-text-secondary mt-2">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center space-x-4">
            {actions}
          </div>
        )}
      </div>
    </div>
  )
)
PageHeader.displayName = "PageHeader"

export { PageHeader }
