export default function Loading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="h-8 w-56 animate-pulse rounded-xl bg-card/40" />
        <div className="h-5 w-96 max-w-full animate-pulse rounded-xl bg-card/40" />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="h-28 animate-pulse rounded-xl border border-border/50 bg-card/30 shadow-xl backdrop-blur-xl"
          />
        ))}
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-9 w-28 animate-pulse rounded-xl bg-card/40" />
          ))}
        </div>
        <div className="mt-4 h-56 animate-pulse rounded-xl border border-border/50 bg-card/20" />
      </div>

      <div className="rounded-xl border border-border/50 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
        <div className="mb-4 h-6 w-48 animate-pulse rounded-xl bg-card/40" />
        <div className="overflow-hidden rounded-xl border border-border/50">
          <div className="h-11 animate-pulse border-b border-border/50 bg-card/20" />
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="h-14 animate-pulse border-b border-border/30 bg-card/10 last:border-b-0" />
          ))}
        </div>
      </div>
    </div>
  );
}
