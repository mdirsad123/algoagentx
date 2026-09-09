import { redirect } from "next/navigation";

type SearchParams = Record<string, string | string[] | undefined>;

export default function LegacyFundedHistoryPage({ searchParams = {} }: { searchParams?: SearchParams }) {
  const params = new URLSearchParams();
  params.set("type", "funded");
  Object.entries(searchParams).forEach(([key, value]) => {
    if (key === "type" || value === undefined) return;
    if (Array.isArray(value)) value.forEach((entry) => params.append(key, entry));
    else params.set(key, value);
  });
  redirect(`/backtest-history?${params.toString()}`);
}
