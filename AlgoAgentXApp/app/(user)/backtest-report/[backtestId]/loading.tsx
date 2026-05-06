export default function Loading() {
  return (
    <div className="space-y-4 rounded-2xl border border-border/50 bg-card/30 p-6 shadow-xl backdrop-blur-xl">
      <div className="h-6 w-64 animate-pulse rounded bg-muted/60" />
      <div className="h-40 animate-pulse rounded-xl bg-muted/30" />
      <p className="text-sm text-muted-foreground">Heavy report is loading. Please wait... Loading may take a few minutes on large datasets.</p>
    </div>
  );
}
