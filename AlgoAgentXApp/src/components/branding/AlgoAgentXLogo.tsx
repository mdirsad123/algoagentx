import React from "react";

interface AlgoAgentXLogoProps {
  variant?: "icon" | "wordmark" | "full";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function AlgoAgentXLogo({ 
  variant = "full", 
  size = "md", 
  className = "" 
}: AlgoAgentXLogoProps) {
  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8", 
    lg: "h-10 w-10"
  };

  const textSize = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg"
  };

  const icon = (
    <svg 
      className={`${sizeClasses[size]} ${className}`} 
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 2L2 7L12 12L22 7L12 2Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-white"
      />
      <path
        d="M2 17L12 22L22 17"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-white"
      />
      <path
        d="M2 12L12 17L22 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-white"
      />
      <circle
        cx="12"
        cy="7"
        r="2"
        fill="currentColor"
        className="text-blue-400"
      />
      <circle
        cx="12"
        cy="17"
        r="2"
        fill="currentColor"
        className="text-blue-400"
      />
    </svg>
  );

  const wordmark = (
    <span className={`font-semibold text-white ${textSize[size]} tracking-tight`}>
      AlgoAgentX
    </span>
  );

  switch (variant) {
    case "icon":
      return icon;
    case "wordmark":
      return wordmark;
    case "full":
    default:
      return (
        <div className="flex items-center gap-3">
          {icon}
          {wordmark}
        </div>
      );
  }
}