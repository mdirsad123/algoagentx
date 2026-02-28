"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CalendarDays, TrendingUp, AlertTriangle, CheckCircle } from "lucide-react";
import AppShell from "@/components/layout/AppShell";

export default function ReportsPage() {
  const performanceMetrics = [
    {
      period: "Today",
      pnl: 1250.50,
      trades: 12,
      winRate: 75.0,
      maxDrawdown: -245.80,
    },
    {
      period: "This Week",
      pnl: 8750.25,
      trades: 89,
      winRate: 68.5,
      maxDrawdown: -1250.40,
    },
    {
      period: "This Month",
      pnl: 32150.75,
      trades: 345,
      winRate: 71.2,
      maxDrawdown: -2850.20,
    },
    {
      period: "This Year",
      pnl: 156750.90,
      trades: 1423,
      winRate: 69.8,
      maxDrawdown: -12850.50,
    },
  ];

  const systemLogs = [
    {
      timestamp: "2024-01-07 14:30:25",
      level: "INFO",
      message: "Strategy EMA_Crossover executed successfully",
      details: "Entry: LONG NIFTY @ 23785.50",
    },
    {
      timestamp: "2024-01-07 14:25:18",
      level: "WARNING",
      message: "High volatility detected in BANKNIFTY",
      details: "Volatility index: 24.5%",
    },
    {
      timestamp: "2024-01-07 14:20:45",
      level: "ERROR",
      message: "Failed to connect to broker API",
      details: "Zerodha API timeout - retrying in 30s",
    },
    {
      timestamp: "2024-01-07 14:15:12",
      level: "INFO",
      message: "Daily backup completed",
      details: "Database backup successful",
    },
    {
      timestamp: "2024-01-07 14:10:33",
      level: "INFO",
      message: "AI signal generated",
      details: "BUY signal for RELIANCE with 85% confidence",
    },
  ];

  const getLogIcon = (level: string) => {
    switch (level) {
      case "ERROR":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case "WARNING":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case "INFO":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getLogBadge = (level: string) => {
    switch (level) {
      case "ERROR":
        return <Badge variant="destructive">ERROR</Badge>;
      case "WARNING":
        return <Badge variant="secondary">WARNING</Badge>;
      case "INFO":
        return <Badge variant="default">INFO</Badge>;
      default:
        return <Badge variant="outline">UNKNOWN</Badge>;
    }
  };

  return (
    <AppShell pageTitle="Analytics & Logs">
      <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Analytics & Logs</h1>
        <p className="text-gray-600 mt-2">
          Performance analytics and system monitoring
        </p>
      </div>

      <Tabs defaultValue="performance" className="space-y-6">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="logs">System Logs</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {performanceMetrics.map((metric, index) => (
              <Card key={index}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {metric.period}
                  </CardTitle>
                  <CalendarDays className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-2xl font-bold text-green-600">
                    ₹{metric.pnl.toLocaleString()}
                  </div>
                  <div className="space-y-1 text-xs text-gray-500">
                    <div>Trades: {metric.trades}</div>
                    <div>Win Rate: {metric.winRate}%</div>
                    <div>Max DD: ₹{metric.maxDrawdown.toLocaleString()}</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Performance Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-green-600">₹156,751</div>
                    <div className="text-sm text-gray-500">Total P&L (YTD)</div>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">69.8%</div>
                    <div className="text-sm text-gray-500">Average Win Rate</div>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-red-600">₹12,851</div>
                    <div className="text-sm text-gray-500">Max Drawdown</div>
                  </div>
                </div>

              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>System Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {systemLogs.map((log, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 border rounded-lg">
                    {getLogIcon(log.level)}
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{log.message}</span>
                        {getLogBadge(log.level)}
                      </div>
                      <p className="text-xs text-gray-600">{log.details}</p>
                      <p className="text-xs text-gray-400">{log.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Log Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm">All Logs</Button>
                <Button variant="outline" size="sm">Errors Only</Button>
                <Button variant="outline" size="sm">Warnings Only</Button>
                <Button variant="outline" size="sm">Info Only</Button>
                <Button variant="outline" size="sm">Last 24h</Button>
                <Button variant="outline" size="sm">Last 7d</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Strategy Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>EMA Crossover</span>
                    <span className="text-green-600">+24.5%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Mean Reversion</span>
                    <span className="text-green-600">+18.2%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Momentum</span>
                    <span className="text-red-600">-5.8%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Support Resistance</span>
                    <span className="text-green-600">+31.7%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Sharpe Ratio</span>
                    <span>1.45</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Sortino Ratio</span>
                    <span>1.78</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Calmar Ratio</span>
                    <span>2.12</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Drawdown</span>
                    <span className="text-red-600">-12.2%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>AI Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-900">Market Sentiment</h4>
                  <p className="text-sm text-blue-700">
                    Current market sentiment is bullish with 68% positive signals across major indices.
                  </p>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg">
                  <h4 className="font-medium text-yellow-900">Risk Alert</h4>
                  <p className="text-sm text-yellow-700">
                    High volatility expected in BANKNIFTY due to upcoming earnings reports.
                  </p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-900">Performance Insight</h4>
                  <p className="text-sm text-green-700">
                    EMA Crossover strategy showing consistent performance in trending markets.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      </div>
    </AppShell>
  );
}
