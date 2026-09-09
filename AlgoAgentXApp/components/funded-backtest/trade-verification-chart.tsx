"use client";

import { BarChart3 } from "lucide-react";
import type { TradeChartContextResponse } from "@/lib/api/backtests";
import { formatDateTimeIST, parseApiDateTime } from "@/lib/timezone";

const n = (value: unknown, fallback = 0): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const nullableNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const fmt = (value: unknown, digits = 2): string => {
  const parsed = nullableNumber(value);
  return parsed === null ? "—" : parsed.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

const priceToY = (price: number, minPrice: number, maxPrice: number, height: number, padding: number): number => {
  if (!Number.isFinite(price) || maxPrice <= minPrice) return height / 2;
  return padding + ((maxPrice - price) / (maxPrice - minPrice)) * (height - padding * 2);
};

const nearestIndex = (candles: TradeChartContextResponse["candles"], timestamp?: string | null): number => {
  if (!candles.length || !timestamp) return -1;
  const target = parseApiDateTime(timestamp)?.getTime() ?? Number.NaN;
  if (!Number.isFinite(target)) return -1;
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  candles.forEach((candle, index) => {
    const current = parseApiDateTime(candle.timestamp)?.getTime() ?? Number.NaN;
    const distance = Math.abs(current - target);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
};

export function FundedTradeVerificationChart({
  context,
  currencySymbol,
  svgId = "funded-trade-verification-chart-svg",
}: {
  context: TradeChartContextResponse;
  currencySymbol?: string | null;
  svgId?: string;
}) {
  const candles = context.candles || [];
  const overlays = context.overlays || {};
  const width = 1040;
  const height = 440;
  const padding = 38;
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;

  if (!candles.length) {
    return (
      <div className="flex h-[360px] items-center justify-center rounded-2xl border border-white/10 bg-black/15 p-6 text-center text-sm text-muted-foreground md:h-[460px]">
        <div>
          <BarChart3 className="mx-auto mb-3 h-10 w-10 text-fuchsia-300" />
          <p className="font-semibold text-foreground">No candle data found for this funded trade window.</p>
          <p className="mt-1">Verify market data exists for this instrument and timeframe.</p>
        </div>
      </div>
    );
  }

  const candleGap = candles.length > 1 ? plotWidth / Math.max(candles.length - 1, 1) : 16;
  const candleWidth = Math.max(3, Math.min(12, candleGap * 0.58));
  const prices = candles.flatMap((candle) => [n(candle.high, Number.NaN), n(candle.low, Number.NaN)]);
  [overlays.entry_price, overlays.exit_price, overlays.stop_loss, overlays.target].forEach((value) => {
    const parsed = nullableNumber(value);
    if (parsed !== null) prices.push(parsed);
  });
  const validPrices = prices.filter(Number.isFinite);
  const rawMin = validPrices.length ? Math.min(...validPrices) : 0;
  const rawMax = validPrices.length ? Math.max(...validPrices) : 1;
  const range = Math.max(rawMax - rawMin, 0.0001);
  const minPrice = rawMin - range * 0.08;
  const maxPrice = rawMax + range * 0.08;
  const xForIndex = (index: number) => padding + index * candleGap;
  const entryIndex = nearestIndex(candles, overlays.entry_time);
  const exitIndex = nearestIndex(candles, overlays.exit_time);
  const side = String(overlays.side || "").toUpperCase();
  const exitText = String(overlays.exit_reason || "EXIT").toUpperCase();
  const pnl = n(overlays.pnl, 0);
  const isTp = exitText.includes("TAKE_PROFIT") || exitText.includes("TARGET") || /\bTP\b/.test(exitText) || pnl > 0;
  const isSl = exitText.includes("STOP_LOSS") || exitText.includes("STOPLOSS") || /\bSL\b/.test(exitText) || pnl < 0;
  const entryPrice = nullableNumber(overlays.entry_price);
  const slPrice = nullableNumber(overlays.stop_loss);
  const tpPrice = nullableNumber(overlays.target);

  const lines = [
    { key: "ENTRY", label: side ? `ENTRY ${side}` : "ENTRY", value: entryPrice, color: "#38bdf8" },
    { key: "SL", label: "SL", value: slPrice, color: "#fb7185" },
    { key: "TP", label: "TP", value: tpPrice, color: "#34d399" },
    { key: "EXIT", label: isTp ? "TP HIT" : isSl ? "EXIT SL" : "EXIT", value: nullableNumber(overlays.exit_price), color: isTp ? "#34d399" : isSl ? "#fb7185" : "#facc15" },
  ].filter((line) => line.value !== null) as Array<{ key: string; label: string; value: number; color: string }>;

  return (
    <div className="self-start rounded-2xl border border-white/10 bg-[#12071f]/85 p-3 shadow-inner">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-muted-foreground">
        <span>Entry · Exit · SL · TP verification</span>
        <span>{formatDateTimeIST(candles[0]?.timestamp)} → {formatDateTimeIST(candles[candles.length - 1]?.timestamp)}</span>
      </div>
      <svg id={svgId} viewBox={`0 0 ${width} ${height}`} className="block h-[340px] w-full md:h-[420px] xl:h-[500px]" role="img" aria-label="Funded trade candlestick verification chart">
        <defs>
          <linearGradient id={`${svgId}-bg`} x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stopColor="#1e0b34"/><stop offset="100%" stopColor="#37145f"/></linearGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} rx="18" fill={`url(#${svgId}-bg)`}/>
        {[0,1,2,3,4].map((tick) => {
          const y = padding + tick * (plotHeight / 4);
          const price = maxPrice - tick * ((maxPrice - minPrice) / 4);
          return <g key={tick}><line x1={padding} x2={width-padding} y1={y} y2={y} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 6"/><text x={width-padding+8} y={y+4} fill="rgba(255,255,255,0.55)" fontSize="11">{fmt(price,2)}</text></g>;
        })}
        {candles.map((candle, index) => {
          const open=n(candle.open), high=n(candle.high), low=n(candle.low), close=n(candle.close);
          const x=xForIndex(index), yHigh=priceToY(high,minPrice,maxPrice,height,padding), yLow=priceToY(low,minPrice,maxPrice,height,padding), yOpen=priceToY(open,minPrice,maxPrice,height,padding), yClose=priceToY(close,minPrice,maxPrice,height,padding);
          const bullish=close>=open, bodyY=Math.min(yOpen,yClose), bodyHeight=Math.max(2,Math.abs(yClose-yOpen)), color=bullish?"#34d399":"#fb7185";
          return <g key={`${candle.timestamp}-${index}`}><line x1={x} x2={x} y1={yHigh} y2={yLow} stroke={color} strokeWidth="1.4"/><rect x={x-candleWidth/2} y={bodyY} width={candleWidth} height={bodyHeight} rx="1.5" fill={bullish?"rgba(52,211,153,0.75)":"rgba(251,113,133,0.75)"} stroke={color}/></g>;
        })}
        {lines.map((line,index)=>{const y=priceToY(line.value,minPrice,maxPrice,height,padding); const labelX=padding+8+(index%2)*138; return <g key={line.key}><line x1={padding} x2={width-padding} y1={y} y2={y} stroke={line.color} strokeWidth="1.8" strokeDasharray={line.key==="ENTRY"?"0":"8 6"}/><rect x={labelX} y={y-13} width="126" height="22" rx="11" fill="#160921" stroke={line.color}/><text x={labelX+9} y={y+4} fill={line.color} fontSize="11" fontWeight="700">{line.label} {fmt(line.value,2)}</text></g>})}
        {entryIndex>=0 ? (()=>{const x=xForIndex(entryIndex); const y=priceToY(n(overlays.entry_price,candles[entryIndex]?.close||0),minPrice,maxPrice,height,padding); return <g><line x1={x} x2={x} y1={padding} y2={height-padding} stroke="rgba(56,189,248,0.35)" strokeDasharray="3 5"/><circle cx={x} cy={y} r="6" fill="#38bdf8" stroke="#fff" strokeWidth="2"/></g>})():null}
        {exitIndex>=0 ? (()=>{const x=xForIndex(exitIndex); const y=priceToY(n(overlays.exit_price,candles[exitIndex]?.close||0),minPrice,maxPrice,height,padding); const color=isTp?"#34d399":isSl?"#fb7185":"#c084fc"; return <g><line x1={x} x2={x} y1={padding} y2={height-padding} stroke={color} strokeDasharray="3 5" opacity="0.55"/><rect x={x-7} y={y-7} width="14" height="14" rx="3" fill={color} stroke="#fff" strokeWidth="2"/></g>})():null}
        <text x={padding} y={height-12} fill="rgba(255,255,255,0.55)" fontSize="11">{formatDateTimeIST(candles[0]?.timestamp)} → {formatDateTimeIST(candles[candles.length-1]?.timestamp)} · {currencySymbol || ""}</text>
      </svg>
    </div>
  );
}
