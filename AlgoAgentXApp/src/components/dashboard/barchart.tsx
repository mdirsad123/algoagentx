"use client";

import {
  Bar,
  BarChart as ReBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface BarChartProps {
  type?: "monthly" | "state" | "court";
  data?: { name: string; total: number }[];
  onClick: (data:any) => void; // ✅ Accept data as prop
}

export function BarChart({ type = "monthly", data = [], onClick }: BarChartProps) {
  const hasData = data && data.length > 0;
  
  // Determine bar color based on chart type
  const barColor = type === "court" ? "#38A169" : "blue"; // Green for 'court', blue for others

  return hasData ? (
    <ResponsiveContainer width="100%" height={350}>
      <ReBarChart data={data} barCategoryGap={20}>
        <XAxis
          dataKey="name"
          stroke="#888888"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#888888"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => value.toLocaleString()}
        />
        <Tooltip
          cursor={{ fill: "rgba(0, 0, 0, 0.1)" }}
          contentStyle={{
            backgroundColor: "white",
            border: "1px solid #ccc",
            borderRadius: "5px",
            padding: "5px",
          }}
        />
        <Bar dataKey="total" fill={barColor} radius={[4, 4, 0, 0]} onClick={onClick} />
      </ReBarChart>
    </ResponsiveContainer>
  ) : (
    <div className="text-center text-red-600 py-20">No record found</div>
  );
}
