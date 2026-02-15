"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, DollarSign, Activity, ArrowUp, ArrowDown, Users, Shield, Zap } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui/page-header";
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardDescription, StandardCardContent } from "@/components/ui/standard-card";
import { DashboardSkeleton } from "@/components/ui/loading-skeleton";

interface StatData {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down";
  icon: any;
  color: string;
}

interface SignalData {
  symbol: string;
  signal: string;
  price: number;
  time: string;
  confidence: number;
}

export default function HomePage() {
  const [stats, setStats] = useState<StatData[]>([
    {
      title: "Total Portfolio Value",
      value: "$127,110.86",
      change: "+13.5%",
      trend: "up",
      icon: DollarSign,
      color: "from-blue-500 to-cyan-500",
    },
    {
      title: "Active Strategies",
      value: "12",
      change: "+2",
      trend: "up",
      icon: Activity,
      color: "from-green-500 to-emerald-500",
    },
    {
      title: "Today's P&L",
      value: "+$1,250.50",
      change: "+5.2%",
      trend: "up",
      icon: TrendingUp,
      color: "from-emerald-500 to-green-500",
    },
    {
      title: "Win Rate",
      value: "67.1%",
      change: "-2.1%",
      trend: "down",
      icon: TrendingDown,
      color: "from-orange-500 to-red-500",
    },
  ]);
  const [recentSignals, setRecentSignals] = useState<SignalData[]>([
    { symbol: "NIFTY", signal: "BUY", price: 23785.50, time: "09:15", confidence: 85 },
    { symbol: "BANKNIFTY", signal: "SELL", price: 45890.25, time: "09:20", confidence: 78 },
    { symbol: "RELIANCE", signal: "BUY", price: 2456.80, time: "09:25", confidence: 92 },
  ]);
  const [loading, setLoading] = useState(false);

  // Removed useEffect to prevent API calls that cause slowness
  // TODO: Implement proper dashboard API endpoints when backend is ready

  return (
    <AppShell pageTitle="Dashboard">
      <PageHeader 
        title="Dashboard"
        subtitle="Welcome to AlgoAgentX - Your AI Trading Intelligence Platform"
      />

      <div className="space-y-6">
        {/* Stats Grid - Premium KPI Cards with Gradient Backgrounds */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <Card key={index} className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <div>
                  <CardDescription className="text-gray-500 text-sm font-medium">
                    {stat.title}
                  </CardDescription>
                  <div className="flex items-end space-x-2">
                    <CardTitle className="text-3xl font-bold tracking-tight text-gray-900">
                      {stat.value}
                    </CardTitle>
                    <div className={`flex items-center space-x-1 text-sm ${
                      stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {stat.trend === 'up' ? (
                        <ArrowUp className="h-4 w-4" />
                      ) : (
                        <ArrowDown className="h-4 w-4" />
                      )}
                      <span className="font-medium">{stat.change}</span>
                    </div>
                  </div>
                </div>
                <div className={`p-3 rounded-lg bg-gradient-to-r ${stat.color} text-white`}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-gray-500">vs last month</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Signals */}
          <Card className="lg:col-span-2 hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
            <CardHeader>
              <CardTitle className="text-gray-900">Recent AI Signals</CardTitle>
              <CardDescription className="text-gray-600">
                Latest algorithmic trading signals with confidence scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentSignals.map((signal, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border border-gray-100 rounded-xl hover:border-gray-200 transition-all duration-200 bg-gradient-to-r from-gray-50 to-white">
                    <div className="flex items-center space-x-4">
                      <Badge 
                        variant={signal.signal === 'BUY' ? 'default' : 'destructive'} 
                        className="text-sm font-medium px-3 py-1"
                      >
                        {signal.signal}
                      </Badge>
                      <div>
                        <p className="font-semibold text-gray-900 text-lg">{signal.symbol}</p>
                        <p className="text-gray-600 text-sm">₹{signal.price.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-right space-y-2">
                      <div className="flex items-center justify-end space-x-2">
                        <span className="text-xs text-gray-500">Confidence:</span>
                        <span className={`text-sm font-medium ${
                          signal.confidence >= 80 ? 'text-green-600' : signal.confidence >= 60 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {signal.confidence}%
                        </span>
                      </div>
                      <div className="flex items-center justify-end space-x-4 text-sm text-gray-500">
                        <span>Updated</span>
                        <span className="font-medium text-gray-900">{signal.time}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance Summary */}
          <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
            <CardHeader>
              <CardTitle className="text-gray-900">Performance Summary</CardTitle>
              <CardDescription className="text-gray-600">
                Key metrics overview
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-gray-100">
                <div>
                  <p className="text-gray-600 text-sm">Total Trades</p>
                  <p className="text-gray-900 text-2xl font-bold">1,234</p>
                </div>
                <div className="text-right">
                  <p className="text-green-600 text-sm flex items-center space-x-1 font-medium">
                    <ArrowUp className="h-4 w-4" />
                    <span>+12.5%</span>
                  </p>
                </div>
              </div>
              <div className="flex justify-between items-center p-4 bg-gradient-to-r from-orange-50 to-red-50 rounded-xl border border-gray-100">
                <div>
                  <p className="text-gray-600 text-sm">Max Drawdown</p>
                  <p className="text-gray-900 text-2xl font-bold">-8.2%</p>
                </div>
                <div className="text-right">
                  <p className="text-green-600 text-sm flex items-center space-x-1 font-medium">
                    <ArrowDown className="h-4 w-4" />
                    <span>-2.1%</span>
                  </p>
                </div>
              </div>
              <div className="flex justify-between items-center p-4 bg-gradient-to-r from-emerald-50 to-green-50 rounded-xl border border-gray-100">
                <div>
                  <p className="text-gray-600 text-sm">Sharpe Ratio</p>
                  <p className="text-gray-900 text-2xl font-bold">1.8</p>
                </div>
                <div className="text-right">
                  <p className="text-green-600 text-sm flex items-center space-x-1 font-medium">
                    <ArrowUp className="h-4 w-4" />
                    <span>+0.3</span>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions with Enhanced Design */}
        <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Quick Actions</CardTitle>
            <CardDescription className="text-gray-600">
              Get started with AlgoAgentX
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link
                href="/strategies"
                prefetch={true}
                className="p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-blue-50 hover:to-cyan-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-blue-600 transition-colors">
                      View Strategies
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Browse and analyze trading strategies
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200">
                    <Activity className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/backtest"
                prefetch={true}
                className="p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-green-50 hover:to-emerald-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-green-600 transition-colors">
                      Run Backtest
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Execute and view strategy backtest results
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200">
                    <TrendingUp className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/reports"
                prefetch={true}
                className="p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-purple-600 transition-colors">
                      View Reports
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Check performance analytics
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200">
                    <DollarSign className="h-6 w-6" />
                  </div>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Additional Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="border-gray-200">
            <CardHeader className="pb-2">
              <CardDescription className="text-gray-500 text-sm">Active Users</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">1,234</p>
                  <p className="text-sm text-green-600 font-medium">+12.5% this month</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg text-white">
                  <Users className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-gray-200">
            <CardHeader className="pb-2">
              <CardDescription className="text-gray-500 text-sm">System Uptime</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">99.9%</p>
                  <p className="text-sm text-green-600 font-medium">Excellent</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white">
                  <Shield className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-gray-200">
            <CardHeader className="pb-2">
              <CardDescription className="text-gray-500 text-sm">AI Signals Today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">156</p>
                  <p className="text-sm text-blue-600 font-medium">High activity</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white">
                  <Zap className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
