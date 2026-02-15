"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  ComposedChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Line,
  ReferenceArea,
  ReferenceLine,
  Legend,
} from "recharts";

/* ===== SMALL STAT BOX (EXCEL STYLE) ===== */
function StatBox({
  label,
  value,
  color = "blue",
}: {
  label: string;
  value: string;
  color?: "blue" | "green" | "red";
}) {
  return (
    <div
      className={cn(
        "bg-white px-4 py-3 rounded-md border-l-4 shadow-sm",
        color === "blue" && "border-blue-500",
        color === "green" && "border-green-500",
        color === "red" && "border-red-500"
      )}
    >
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  );
}


const chartData = [
  { time: "09:15", price: 23785, ema20: 23770, ema50: 23765 },
  { time: "09:20", price: 23778, ema20: 23772, ema50: 23767 },
  { time: "09:25", price: 23774, ema20: 23773, ema50: 23769 },
  { time: "09:30", price: 23766, ema20: 23768, ema50: 23768 },
  { time: "09:35", price: 23752, ema20: 23760, ema50: 23766 },
  { time: "09:40", price: 23745, ema20: 23755, ema50: 23764 },
  { time: "09:45", price: 23750, ema20: 23754, ema50: 23763 },
  { time: "09:50", price: 23758, ema20: 23756, ema50: 23762 },
];

const winLossData = [
  { name: "Win", value: 67.1 },
  { name: "Loss", value: 32.9 },
];

const COLORS = ["#2563eb", "#93c5fd"];

const equityData = [
  { date: "Jan", equity: 100000 },
  { date: "Feb", equity: 112000 },
  { date: "Mar", equity: 118000 },
  { date: "Apr", equity: 130000 },
  { date: "May", equity: 145000 },
  { date: "Jun", equity: 160000 },
  { date: "Jul", equity: 170000 },
  { date: "Aug", equity: 182000 },
  { date: "Sep", equity: 195000 },
  { date: "Oct", equity: 215000 },
  { date: "Nov", equity: 235000 },
];


export default function BacktestPage() {
  const [range, setRange] = useState("1M");

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <h1 className="text-2xl font-bold text-gray-800">Backtest</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <Select>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Select Strategy" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="strategy1">Strategy 1</SelectItem>
            <SelectItem value="strategy2">Strategy 2</SelectItem>
          </SelectContent>
        </Select>

        <Select>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Select Instrument" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="nifty">NIFTY</SelectItem>
            <SelectItem value="banknifty">BANKNIFTY</SelectItem>
          </SelectContent>
        </Select>

        <Select>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Timeframe" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="5m">5 Min</SelectItem>
            <SelectItem value="15m">15 Min</SelectItem>
            <SelectItem value="1h">1 Hour</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Range Buttons */}
      <div className="flex gap-3">
        {["1M", "6M", "1Y", "Custom"].map((item) => (
          <Button
            key={item}
            variant={range === item ? "default" : "outline"}
            onClick={() => setRange(item)}
          >
            {item}
          </Button>
        ))}
      </div>

      {/* ================= STRATEGY SUMMARY (FIXED) ================= */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">
          📊 Strategy Summary
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* COLUMN 1 */}
          <div className="space-y-3">
            <StatBox label="Initial Capital" value="100000" color="blue" />
            <StatBox label="Net Profit" value="17171.71" color="green" />
            <StatBox label="Losing Trades" value="53" color="red" />
            <StatBox label="Max Drawdown" value="5245.22" color="red" />
            <StatBox label="Profit Factor" value="3.53" color="blue" />
          </div>

          {/* COLUMN 2 */}
          <div className="space-y-3">
            <StatBox label="Final Capital" value="127110.86" color="blue" />
            <StatBox label="Total Trades" value="161" color="blue" />
            <StatBox label="Win %" value="67.08" color="green" />
            <StatBox label="Max Loss" value="-2726.71" color="red" />
            <StatBox label="Sharpe Ratio" value="0.72" color="blue" />
          </div>

          {/* COLUMN 3 */}
          <div className="space-y-3">
            <StatBox label="Total P&L" value="17171.86" color="green" />
            <StatBox label="Winning Trades" value="108”" color="green" />
            <StatBox label="Avg Profit / Trade" value="106.53" color="green" />
            <StatBox label="Max Drawdown %" value="-2.24" color="red" />
            <StatBox label="Risk Reward" value="1 : 2" color="blue" />
          </div>
        </div>
      </div>
      {/* ================= END SUMMARY ================= */}

      {/* Charts */}
       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Win vs Loss */}
      <Card className="shadow-sm">
        <CardContent className="p-4 h-72">
  {/* Header Row */}
  <div className="flex items-center justify-between mb-2">
    <h3 className="text-sm font-semibold text-gray-700">
      🟠 Win vs Loss
    </h3>

    <div className="flex gap-4 text-sm">
      <span className="text-blue-600 font-medium">■ Win 67.1%</span>
      <span className="text-blue-300 font-medium">■ Loss 32.9%</span>
    </div>
  </div>

  {/* Chart */}
  <ResponsiveContainer width="100%" height="100%">
    <PieChart>
      <Pie
        data={winLossData}
        cx="50%"
        cy="50%"
        innerRadius={55}
        outerRadius={90}
        dataKey="value"
        paddingAngle={4}
      >
        {winLossData.map((_, index) => (
          <Cell key={index} fill={COLORS[index]} />
        ))}
      </Pie>
      <Tooltip />
    </PieChart>
  </ResponsiveContainer>
</CardContent>

      </Card>

      {/* Equity Curve */}
      <Card className="shadow-sm">
        <CardContent className="p-4 h-72">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            📈 Equity Curve
          </h3>

          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equityData}>
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>

      {/* Trade History */}
      <Card>
        <CardContent className="p-4">
          <h2 className="font-semibold mb-4">Trade History</h2>
          <div className="overflow-auto">
            <table className="w-full text-sm border">
              <thead className="bg-gray-100">
                <tr>
                  <th className="p-2 border">Entry Time</th>
                  <th className="p-2 border">Exit Time</th>
                  <th className="p-2 border">Type</th>
                  <th className="p-2 border">Qty</th>
                  <th className="p-2 border">P&L</th>
                  <th className="p-2 border">Result</th>
                </tr>
              </thead>
              <tbody>
                <tr className="text-center">
                  <td className="p-2 border">02-01-2025 09:30</td>
                  <td className="p-2 border">02-01-2025 09:45</td>
                  <td className="p-2 border">LONG</td>
                  <td className="p-2 border">1</td>
                  <td className="p-2 border text-green-600">+850</td>
                  <td className="p-2 border">WIN</td>
                </tr>
                <tr className="text-center">
                  <td className="p-2 border">02-01-2025 10:15</td>
                  <td className="p-2 border">02-01-2025 10:25</td>
                  <td className="p-2 border">SHORT</td>
                  <td className="p-2 border">1</td>
                  <td className="p-2 border text-red-600">-420</td>
                  <td className="p-2 border">LOSS</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ================= TRADE DETAIL SECTION ================= */}
 
     
    <Card>
      <CardContent className="p-4 space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Trade Detail</h2>

          <Select defaultValue="0">
            <SelectTrigger className="w-60">
              <SelectValue placeholder="Select Trade Index" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">Trade #0</SelectItem>
              <SelectItem value="1">Trade #1</SelectItem>
              <SelectItem value="2">Trade #2</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Trade Title */}
        <div className="text-sm font-medium text-gray-700">
          Trade #0 | <span className="text-green-600 font-semibold">LONG</span>
        </div>

        {/* Chart */}
        <div className="relative h-[380px] bg-white border rounded-md">

          {/* Legend (INLINE) */}
          <div className="absolute right-3 top-3 bg-white border rounded-md p-2 text-xs space-y-1 shadow z-10">
            <div className="flex items-center gap-2">
              <span className="w-3 h-[2px] bg-black" /> Price
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-[2px] bg-blue-500" /> EMA 20
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-[2px] bg-purple-500" /> EMA 50
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-[2px] bg-green-600" /> Entry
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-[2px] bg-red-600" /> Exit
            </div>
          </div>

          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip />

              {/* Profit Zone */}
              <ReferenceArea y1={23775} y2={23820} fill="#bbf7d0" fillOpacity={0.6} />

              {/* Loss Zone */}
              <ReferenceArea y1={23720} y2={23775} fill="#fecaca" fillOpacity={0.6} />

              {/* Price */}
              <Line dataKey="price" stroke="#000000" dot={false} strokeWidth={2} />

              {/* EMA */}
              <Line dataKey="ema20" stroke="#3b82f6" dot={false} strokeWidth={2} />
              <Line dataKey="ema50" stroke="#a855f7" dot={false} strokeWidth={2} />

              {/* Entry / Exit */}
              <ReferenceLine y={23775} stroke="#16a34a" strokeWidth={2} />
              <ReferenceLine y={23745} stroke="#dc2626" strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Trade Details Text */}
        <div className="bg-gray-50 border rounded-md p-4 text-xs font-mono whitespace-pre-wrap text-gray-800">
{`{
  "Entry Time": "2024-12-26 09:15:00",
  "Exit Time": "2024-12-26 10:30:00",
  "Direction": "LONG",
  "Entry Price": 23785.8,
  "Exit Price": 23728.48,
  "Stop Loss": 23745.0,
  "Target": 23870.0,
  "PnL": -1008,
  "Result": "LOSS"
}`}
        </div>

      </CardContent>
    </Card>
{/* ================= END TRADE DETAIL ================= */}

    </div>
  );
}
