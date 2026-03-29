"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Card className="bg-card/30 backdrop-blur-xl border border-border/50 shadow-xl rounded-xl p-8 text-center">
      <div className="space-y-4">
        <div className="space-y-2">
          <h3 className="text-xl font-semibold bg-gradient-to-r from-white via-purple-200 to-purple-300 bg-clip-text text-transparent">
            {title}
          </h3>
          <p className="text-purple-300 text-sm">
            {description}
          </p>
        </div>
        {action && (
          <div className="pt-4">
            {action}
          </div>
        )}
      </div>
    </Card>
  );
}