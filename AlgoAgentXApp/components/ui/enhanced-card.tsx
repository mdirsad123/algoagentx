import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { cssCustomProperties } from "./design-tokens"

// Type for CSS custom properties
type CSSCustomProperties = {
  [key: `--${string}`]: string;
}

const cardVariants = cva(
  "rounded-lg border shadow-sm transition-all duration-200",
  {
    variants: {
      variant: {
        default: "border-neutral-200 bg-white text-neutral-900 dark:border-dark-border dark:bg-dark-surface dark:text-dark-text-primary",
        elevated: "border-neutral-200 bg-white shadow-lg hover:shadow-xl text-neutral-900 dark:border-dark-border dark:bg-dark-surface dark:text-dark-text-primary",
        outlined: "border-2 border-primary-500 bg-white text-neutral-900 dark:border-primary-500 dark:bg-dark-surface dark:text-dark-text-primary",
        subtle: "border-neutral-100 bg-neutral-50 text-neutral-900 dark:border-dark-border dark:bg-dark-surface-2 dark:text-dark-text-primary",
      },
      padding: {
        sm: "p-4",
        md: "p-6",
        lg: "p-8",
        none: "p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "md",
    },
  }
)

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  children: React.ReactNode
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding, className }))}
      style={cssCustomProperties as React.CSSProperties}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex flex-col space-y-1.5 p-6 pb-4",
      className
    )}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight text-neutral-900",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-neutral-600", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-4", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }