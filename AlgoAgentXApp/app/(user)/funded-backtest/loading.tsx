export default function Loading() {
  return <div className="mx-auto w-full max-w-[1600px] space-y-6 p-6"><div className="h-10 w-72 animate-pulse rounded-xl bg-white/10" /><div className="grid gap-4 md:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-2xl bg-white/5" />)}</div><div className="grid gap-6 xl:grid-cols-2"><div className="h-[520px] animate-pulse rounded-2xl bg-white/5" /><div className="h-[520px] animate-pulse rounded-2xl bg-white/5" /></div></div>;
}
