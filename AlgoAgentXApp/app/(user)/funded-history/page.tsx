import { redirect } from "next/navigation";

export default function LegacyFundedHistoryAliasPage() {
  redirect("/backtest-history?type=funded");
}
