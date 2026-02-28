"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, DollarSign, Activity, ArrowUp, ArrowDown, Users, Shield, Zap, BarChart3, PlayCircle, FileText } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui/page-header";
import { ModernCard, ModernCardHeader, ModernCardTitle, ModernCardDescription, ModernCardContent } from "@/components/ui/modern-card";

interface StatData {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down";
  icon: any;
  variant?: "default" | "highlight" | "subtle";
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
      variant: "highlight",
    },
    {
      title: "Active Strategies",
      value: "12",
      change: "+2",
      trend: "up",
      icon: Activity,
      variant: "default",
    },
    {
      title: "Today's P&L",
      value: "+$1,250.50",
      change: "+5.2%",
      trend: "up",
      icon: TrendingUp,
      variant: "default",
    },
    {
      title: "Win Rate",
      value: "67.1%",
      change: "-2.1%",
      trend: "down",
      icon: TrendingDown,
      variant: "subtle",
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
      
      {/* Stats Grid - 12-column responsive grid with consistent card heights */}
        <div className="grid grid-cols-12 gap-6">
          {/* Portfolio Value - Takes 3 columns on large screens, full width on mobile */}
          <ModernCard className="col-span-12 lg:col-span-3 h-full" variant="highlight">
            <ModernCardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <ModernCardDescription className="text-sm font-medium text-gray-600">
                    Total Portfolio Value
                  </ModernCardDescription>
                  <div className="flex items-end space-x-2 mt-1">
                    <ModernCardTitle className="text-2xl font-bold text-gray-900">
                      $127,110.86
                    </ModernCardTitle>
                    <div className="flex items-center space-x-1 text-sm text-green-600">
                      <ArrowUp className="h-4 w-4" />
                      <span className="font-medium">+13.5%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white shadow-lg">
                  <DollarSign className="h-6 w-6" />
                </div>
              </div>
            </ModernCardHeader>
            <ModernCardContent>
              <p className="text-xs text-gray-500">vs last month</p>
            </ModernCardContent>
          </ModernCard>

          {/* Active Strategies - Takes 3 columns */}
          <ModernCard className="col-span-12 lg:col-span-3 h-full" variant="default">
            <ModernCardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <ModernCardDescription className="text-sm font-medium text-gray-600">
                    Active Strategies
                  </ModernCardDescription>
                  <div className="flex items-end space-x-2 mt-1">
                    <ModernCardTitle className="text-2xl font-bold text-gray-900">
                      12
                    </ModernCardTitle>
                    <div className="flex items-center space-x-1 text-sm text-green-600">
                      <ArrowUp className="h-4 w-4" />
                      <span className="font-medium">+2</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white shadow-lg">
                  <Activity className="h-6 w-6" />
                </div>
              </div>
            </ModernCardHeader>
            <ModernCardContent>
              <p className="text-xs text-gray-500">Currently running</p>
            </ModernCardContent>
          </ModernCard>

          {/* Today's P&L - Takes 3 columns */}
          <ModernCard className="col-span-12 lg:col-span-3 h-full" variant="default">
            <ModernCardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <ModernCardDescription className="text-sm font-medium text-gray-600">
                    Today's P&L
                  </ModernCardDescription>
                  <div className="flex items-end space-x-2 mt-1">
                    <ModernCardTitle className="text-2xl font-bold text-gray-900">
                      +$1,250.50
                    </ModernCardTitle>
                    <div className="flex items-center space-x-1 text-sm text-green-600">
                      <ArrowUp className="h-4 w-4" />
                      <span className="font-medium">+5.2%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg text-white shadow-lg">
                  <TrendingUp className="h-6 w-6" />
                </div>
              </div>
            </ModernCardHeader>
            <ModernCardContent>
              <p className="text-xs text-gray-500">Real-time updates</p>
            </ModernCardContent>
          </ModernCard>

          {/* Win Rate - Takes 3 columns */}
          <ModernCard className="col-span-12 lg:col-span-3 h-full" variant="subtle">
            <ModernCardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <ModernCardDescription className="text-sm font-medium text-gray-600">
                    Win Rate
                  </ModernCardDescription>
                  <div className="flex items-end space-x-2 mt-1">
                    <ModernCardTitle className="text-2xl font-bold text-gray-900">
                      67.1%
                    </ModernCardTitle>
                    <div className="flex items-center space-x-1 text-sm text-red-600">
                      <ArrowDown className="h-4 w-4" />
                      <span className="font-medium">-2.1%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg text-white shadow-lg">
                  <TrendingDown className="h-6 w-6" />
                </div>
              </div>
            </ModernCardHeader>
            <ModernCardContent>
              <p className="text-xs text-gray-500">Last 30 days</p>
            </ModernCardContent>
          </ModernCard>
        </div>

        {/* Main Content Grid - 12-column layout */}
        <div className="grid grid-cols-12 gap-6">
          {/* Recent AI Signals - Takes 8 columns on large screens */}
          <ModernCard className="col-span-12 lg:col-span-8">
            <ModernCardHeader>
              <ModernCardTitle>Recent AI Signals</ModernCardTitle>
              <ModernCardDescription>
                Latest algorithmic trading signals with confidence scores
              </ModernCardDescription>
            </ModernCardHeader>
            <ModernCardContent>
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
            </ModernCardContent>
          </ModernCard>

          {/* Performance Summary - Takes 4 columns on large screens */}
          <ModernCard className="col-span-12 lg:col-span-4">
            <ModernCardHeader>
              <ModernCardTitle>Performance Summary</ModernCardTitle>
              <ModernCardDescription>
                Key metrics overview
              </ModernCardDescription>
            </ModernCardHeader>
            <ModernCardContent className="space-y-4">
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
            </ModernCardContent>
          </ModernCard>
        </div>

        {/* Quick Actions - 12-column grid */}
        <ModernCard>
          <ModernCardHeader>
            <ModernCardTitle>Quick Actions</ModernCardTitle>
            <ModernCardDescription>
              Get started with AlgoAgentX
            </ModernCardDescription>
          </ModernCardHeader>
          <ModernCardContent>
            <div className="grid grid-cols-12 gap-6">
              <Link
                href="/strategies"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-blue-50 hover:to-cyan-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-blue-600 transition-colors">
                      View Strategies
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Browse and analyze trading strategies
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg">
                    <BarChart3 className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/backtest"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-green-50 hover:to-emerald-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-green-600 transition-colors">
                      Run Backtest
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Execute and view strategy backtest results
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg">
                    <PlayCircle className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/reports"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg group-hover:text-purple-600 transition-colors">
                      View Reports
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Check performance analytics
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg">
                    <FileText className="h-6 w-6" />
                  </div>
                </div>
              </Link>
            </div>
          </ModernCardContent>
        </ModernCard>

        {/* Additional Stats Row - 12-column grid */}
        <div className="grid grid-cols-12 gap-6">
          <ModernCard className="col-span-12 md:col-span-4">
            <ModernCardHeader>
              <ModernCardDescription className="text-sm font-medium text-gray-600">
                Active Users
              </ModernCardDescription>
            </ModernCardHeader>
            <ModernCardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">1,234</p>
                  <p className="text-sm text-green-600 font-medium">+12.5% this month</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg text-white shadow-lg">
                  <Users className="h-6 w-6" />
                </div>
              </div>
            </ModernCardContent>
          </ModernCard>
          
          <ModernCard className="col-span-12 md:col-span-4">
            <ModernCardHeader>
              <ModernCardDescription className="text-sm font-medium text-gray-600">
                System Uptime
              </ModernCardDescription>
            </ModernCardHeader>
            <ModernCardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">99.9%</p>
                  <p className="text-sm text-green-600 font-medium">Excellent</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white shadow-lg">
                  <Shield className="h-6 w-6" />
                </div>
              </div>
            </ModernCardContent>
          </ModernCard>
          
          <ModernCard className="col-span-12 md:col-span-4">
            <ModernCardHeader>
              <ModernCardDescription className="text-sm font-medium text-gray-600">
                AI Signals Today
              </ModernCardDescription>
            </ModernCardHeader>
            <ModernCardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">156</p>
                  <p className="text-sm text-blue-600 font-medium">High activity</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white shadow-lg">
                  <Zap className="h-6 w-6" />
                </div>
              </div>
            </ModernCardContent>
          </ModernCard>
        </div>
      </div>
    </AppShell>
  );
}
