"use client";

import {
  PieChart as RePieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  PieLabelRenderProps,
} from "recharts";

interface PieChartProps {
  data: number[];
  labels: string[];
  colors: string[];
  textColor?: string | string[];
  onSliceClick?: (label: string) => void;
}

export function PieChart({ data, labels, colors, textColor = "#000", onSliceClick }: PieChartProps) {
  // No filtering here, keeping all data as is (including zeros)
  const pieData = labels.map((label, index) => ({
    name: label,
    value: data[index],
  }));

  const renderCustomizedLabel = ({
    cx = 0,
    cy = 0,
    midAngle = 0,
    innerRadius = 0,
    outerRadius = 0,
    index,
  }: PieLabelRenderProps) => {
    const RADIAN = Math.PI / 180;
    const radius =
      Number(innerRadius) + (Number(outerRadius) - Number(innerRadius)) * 0.5;
    const x = Number(cx) + radius * Math.cos(-midAngle * RADIAN);
    const y = Number(cy) + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill={Array.isArray(textColor) ? textColor[index ?? 0] : textColor}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={12}
      >
        {pieData[index ?? 0].name}
      </text>
    );
  };

  const hasData = pieData.some((item) => item.value > 0); // Check if there is any data to render

  return hasData ? (
    <ResponsiveContainer width="100%" height={350}>
      <RePieChart width={400} height={400} className="-mt-10">
        <Pie
          data={pieData}
          cx="50%"
          cy="50%"
          innerRadius={0}
          outerRadius={120}
          paddingAngle={1}
          dataKey="value"
          label={renderCustomizedLabel}
          labelLine={false}
          onClick={(e) => {
            if (onSliceClick && e?.name) onSliceClick(e.name); // Handle slice click
          }}
        >
          {pieData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} /> // Maintain colors
          ))}
        </Pie>
        <Tooltip />
      </RePieChart>
    </ResponsiveContainer>
  ) : (
    <div className="text-center text-red-600 py-20">No record found</div>
  );
}
