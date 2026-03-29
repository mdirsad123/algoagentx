import { GlassCard } from "@/components/ui/GlassCard";

export default function Loading() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-2">
        <div className="h-9 w-48 bg-white/20 rounded animate-pulse"></div>
        <div className="h-5 w-80 bg-white/20 rounded animate-pulse"></div>
      </div>

      {/* Tabs */}
      <div className="bg-card/30 border border-border/50 rounded-lg p-2">
        <div className="flex space-x-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 w-24 bg-white/20 rounded animate-pulse"></div>
          ))}
        </div>
      </div>

      {/* Content Area */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[...Array(4)].map((_, index) => (
          <GlassCard key={index} className="animate-pulse">
            <div className="p-6">
              <div className="h-6 bg-white/20 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-white/20 rounded w-full mb-4"></div>
              <div className="space-y-3 mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-4 bg-white/20 rounded"></div>
                    ))}
                  </div>
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-4 bg-white/20 rounded"></div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="h-10 bg-white/20 rounded animate-pulse"></div>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}