"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { cssCustomProperties } from "./design-tokens";

interface ModernCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: "default" | "highlight" | "subtle";
  hoverEffect?: boolean;
  border?: boolean;
  shadow?: boolean;
}

const ModernCard = React.forwardRef<HTMLDivElement, ModernCardProps>(
  ({ 
    className, 
    children, 
    variant = "default", 
    hoverEffect = true,
    border = true,
    shadow = true,
    ...props 
  }, ref) => {
    const baseClasses = "bg-white rounded-xl transition-all duration-300";
    
    const variantClasses = {
      default: "border border-gray-100",
      highlight: "border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white",
      subtle: "border border-gray-50 bg-gray-50/50"
    };

    const hoverClasses = hoverEffect 
      ? "hover:shadow-lg hover:shadow-blue-500/10 hover:-translate-y-1 hover:border-gray-200" 
      : "";

    const shadowClasses = shadow ? "shadow-sm" : "";

    return (
      <div
        ref={ref}
        className={cn(
          baseClasses,
          variantClasses[variant],
          border && "border",
          shadowClasses,
          hoverClasses,
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ModernCard.displayName = "ModernCard";

interface ModernCardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const ModernCardHeader = React.forwardRef<HTMLDivElement, ModernCardHeaderProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("p-6 pb-4", className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ModernCardHeader.displayName = "ModernCardHeader";

interface ModernCardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

const ModernCardTitle = React.forwardRef<HTMLHeadingElement, ModernCardTitleProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <h3
        ref={ref}
        className={cn(
          "text-lg font-semibold text-gray-900 tracking-tight",
          className
        )}
        {...props}
      >
        {children}
      </h3>
    );
  }
);

ModernCardTitle.displayName = "ModernCardTitle";

interface ModernCardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

const ModernCardDescription = React.forwardRef<HTMLParagraphElement, ModernCardDescriptionProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn("text-sm text-gray-600", className)}
        {...props}
      >
        {children}
      </p>
    );
  }
);

ModernCardDescription.displayName = "ModernCardDescription";

interface ModernCardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const ModernCardContent = React.forwardRef<HTMLDivElement, ModernCardContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("p-6 pt-0", className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ModernCardContent.displayName = "ModernCardContent";

export { ModernCard, ModernCardHeader, ModernCardTitle, ModernCardDescription, ModernCardContent };