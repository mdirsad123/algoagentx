import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { cssCustomProperties } from "./design-tokens"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary-500 text-white shadow-sm hover:bg-primary-600 focus-visible:ring-primary-500 dark:bg-primary-600 dark:hover:bg-primary-700",
        destructive: "bg-danger-500 text-white shadow-sm hover:bg-danger-600 focus-visible:ring-danger-500 dark:bg-danger-600 dark:hover:bg-danger-700",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500 dark:border-dark-border dark:bg-dark-surface dark:hover:bg-dark-surface-2 dark:text-dark-text-primary",
        secondary: "bg-secondary-100 text-secondary-900 shadow-sm hover:bg-secondary-200 focus-visible:ring-secondary-500 dark:bg-dark-surface dark:text-dark-text-primary dark:hover:bg-dark-surface-2",
        ghost: "hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500 dark:hover:bg-dark-surface-2 dark:hover:text-dark-text-primary",
        link: "text-primary-600 underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500 dark:text-primary-400",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3 text-sm",
        lg: "h-11 rounded-md px-8 text-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        style={cssCustomProperties as React.CSSProperties}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }