"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { 
  TrendingUp, TrendingDown, DollarSign, Activity, ArrowUp, ArrowDown, 
  Users, Shield, Zap, BarChart3, PlayCircle, FileText 
} from "lucide-react";
import { PageShell } from "@/components/ui/PageShell";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";

interface SignalData {
  symbol: string;
  signal: string;
  price: number;
  time: string;
  confidence: number;
}

export default function HomePage() {
  const [recentSignals] = useState<SignalData[]>([
    { symbol: "NIFTY", signal: "BUY", price: 23785.50, time: "09:15", confidence: 85 },
    { symbol: "BANKNIFTY", signal: "SELL", price: 45890.25, time: "09:20", confidence: 78 },
    { symbol: "RELIANCE", signal: "BUY", price: 2456.80, time: "09:25", confidence: 92 },
  ]);

  return (
    <>
      <PageHeader 
        title="Dashboard"
        subtitle="Welcome to AlgoAgentX - Your AI Trading Intelligence Platform"
      />

      <div className="space-y-6">
        {/* Stats Grid - 12-column responsive grid with consistent card heights */}
        <div className="grid grid-cols-12 gap-6">
          {/* Portfolio Value - Takes 3 columns on large screens, full width on mobile */}
          <GlassCard className="col-span-12 lg:col-span-3 h-full">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium tracking-wide uppercase">
                    Total Portfolio Value
                  </p>
                  <div className="flex items-end space-x-3 mt-2">
                    <h3 className="text-3xl font-bold text-white drop-shadow-lg">
                      $127,110.86
                    </h3>
                    <div className="flex items-center space-x-2 bg-green-500/20 border border-green-500/40 px-3 py-1 rounded-full">
                      <ArrowUp className="h-4 w-4 text-green-400" />
                      <span className="font-semibold text-green-400">+13.5%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white shadow-lg shadow-blue-500/30">
                  <DollarSign className="h-6 w-6" />
                </div>
              </div>
              <p className="text-purple-200 text-xs mt-2 font-medium tracking-wide">vs last month</p>
            </div>
          </GlassCard>

          {/* Active Strategies - Takes 3 columns */}
          <GlassCard className="col-span-12 lg:col-span-3 h-full">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium tracking-wide uppercase">
                    Active Strategies
                  </p>
                  <div className="flex items-end space-x-3 mt-2">
                    <h3 className="text-3xl font-bold text-white drop-shadow-lg">
                      12
                    </h3>
                    <div className="flex items-center space-x-2 bg-green-500/20 border border-green-500/40 px-3 py-1 rounded-full">
                      <ArrowUp className="h-4 w-4 text-green-400" />
                      <span className="font-semibold text-green-400">+2</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white shadow-lg shadow-green-500/30">
                  <Activity className="h-6 w-6" />
                </div>
              </div>
              <p className="text-purple-200 text-xs mt-2 font-medium tracking-wide">Currently running</p>
            </div>
          </GlassCard>

          {/* Today's P&L - Takes 3 columns */}
          <GlassCard className="col-span-12 lg:col-span-3 h-full">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium tracking-wide uppercase">
                    Today's P&L
                  </p>
                  <div className="flex items-end space-x-3 mt-2">
                    <h3 className="text-3xl font-bold text-white drop-shadow-lg">
                      +$1,250.50
                    </h3>
                    <div className="flex items-center space-x-2 bg-green-500/20 border border-green-500/40 px-3 py-1 rounded-full">
                      <ArrowUp className="h-4 w-4 text-green-400" />
                      <span className="font-semibold text-green-400">+5.2%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg text-white shadow-lg shadow-emerald-500/30">
                  <TrendingUp className="h-6 w-6" />
                </div>
              </div>
              <p className="text-purple-200 text-xs mt-2 font-medium tracking-wide">Real-time updates</p>
            </div>
          </GlassCard>

          {/* Win Rate - Takes 3 columns */}
          <GlassCard className="col-span-12 lg:col-span-3 h-full">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium tracking-wide uppercase">
                    Win Rate
                  </p>
                  <div className="flex items-end space-x-3 mt-2">
                    <h3 className="text-3xl font-bold text-white drop-shadow-lg">
                      67.1%
                    </h3>
                    <div className="flex items-center space-x-2 bg-red-500/20 border border-red-500/40 px-3 py-1 rounded-full">
                      <ArrowDown className="h-4 w-4 text-red-400" />
                      <span className="font-semibold text-red-400">-2.1%</span>
                    </div>
                  </div>
                </div>
                <div className="p-3 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg text-white shadow-lg shadow-orange-500/30">
                  <TrendingDown className="h-6 w-6" />
                </div>
              </div>
              <p className="text-purple-200 text-xs mt-2 font-medium tracking-wide">Last 30 days</p>
            </div>
          </GlassCard>
        </div>

        {/* Main Content Grid - 12-column layout */}
        <div className="grid grid-cols-12 gap-6">
          {/* Recent AI Signals - Takes 8 columns on large screens */}
          <GlassCard className="col-span-12 lg:col-span-8">
            <div className="p-6">
              <div className="mb-4">
                <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">
                  Recent AI Signals
                </h3>
                <p className="text-purple-200 text-sm font-medium tracking-wide">
                  Latest algorithmic trading signals with confidence scores
                </p>
              </div>
              <div className="space-y-4">
                {recentSignals.map((signal, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border border-white/20 rounded-xl hover:border-white/40 transition-all duration-300 hover:scale-105">
                    <div className="flex items-center space-x-4">
                      <Badge 
                        variant={signal.signal === 'BUY' ? 'default' : 'destructive'} 
                        className="text-sm font-bold px-4 py-2 text-lg tracking-wide border-2"
                      >
                        {signal.signal}
                      </Badge>
                      <div>
                        <p className="font-bold text-white text-xl tracking-wide">{signal.symbol}</p>
                        <p className="text-purple-200 text-sm font-medium">₹{signal.price.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-right space-y-2">
                      <div className="text-right space-y-1">
                        <div className="flex items-center justify-end space-x-3">
                          <span className="text-xs text-purple-300 font-medium">Confidence:</span>
                          <span className={`text-sm font-bold px-2 py-1 rounded ${
                            signal.confidence >= 80 ? 'bg-green-500/20 text-green-400 border border-green-500/40' : 
                            signal.confidence >= 60 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' : 
                            'bg-red-500/20 text-red-400 border border-red-500/40'
                          }`}>
                            {signal.confidence}%
                          </span>
                        </div>
                        <div className="flex items-center justify-end space-x-4 text-xs text-purple-300 font-medium">
                          <span>Updated</span>
                          <span className="font-bold text-white">{signal.time}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>

          {/* Performance Summary - Takes 4 columns on large screens */}
          <GlassCard className="col-span-12 lg:col-span-4">
            <div className="p-6">
              <div className="mb-4">
                <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">
                  Performance Summary
                </h3>
                <p className="text-purple-200 text-sm font-medium tracking-wide">
                  Key metrics overview
                </p>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-xl border border-white/20">
                  <div>
                    <p className="text-purple-200 text-sm font-medium tracking-wide">Total Trades</p>
                    <p className="text-white text-3xl font-bold tracking-tight">1,234</p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 text-sm flex items-center space-x-2 font-bold">
                      <ArrowUp className="h-4 w-4" />
                      <span>+12.5%</span>
                    </p>
                  </div>
                </div>
                <div className="flex justify-between items-center p-4 bg-gradient-to-r from-orange-500/20 to-red-500/20 rounded-xl border border-white/20">
                  <div>
                    <p className="text-purple-200 text-sm font-medium tracking-wide">Max Drawdown</p>
                    <p className="text-white text-3xl font-bold tracking-tight">-8.2%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 text-sm flex items-center space-x-2 font-bold">
                      <ArrowDown className="h-4 w-4" />
                      <span>-2.1%</span>
                    </p>
                  </div>
                </div>
                <div className="flex justify-between items-center p-4 bg-gradient-to-r from-emerald-500/20 to-green-500/20 rounded-xl border border-white/20">
                  <div>
                    <p className="text-purple-200 text-sm font-medium tracking-wide">Sharpe Ratio</p>
                    <p className="text-white text-3xl font-bold tracking-tight">1.8</p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-400 text-sm flex items-center space-x-2 font-bold">
                      <ArrowUp className="h-4 w-4" />
                      <span>+0.3</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Quick Actions - 12-column grid */}
        <GlassCard>
          <div className="p-6">
            <div className="mb-4">
                <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">
                  Quick Actions
                </h3>
                <p className="text-purple-200 text-sm font-medium tracking-wide">
                  Get started with AlgoAgentX
                </p>
            </div>
            <div className="grid grid-cols-12 gap-6">
              <Link
                href="/strategies"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-white/20 rounded-xl hover:border-white/40 hover:scale-105 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-bold text-white text-lg group-hover:text-blue-300 transition-colors tracking-wide">
                      View Strategies
                    </h3>
                    <p className="text-purple-200 text-sm mt-2 font-medium tracking-wide">
                      Browse and analyze trading strategies
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg shadow-blue-500/30">
                    <BarChart3 className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/backtest"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-white/20 rounded-xl hover:border-white/40 hover:scale-105 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-bold text-white text-lg group-hover:text-green-300 transition-colors tracking-wide">
                      Run Backtest
                    </h3>
                    <p className="text-purple-200 text-sm mt-2 font-medium tracking-wide">
                      Execute and view strategy backtest results
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg shadow-green-500/30">
                    <PlayCircle className="h-6 w-6" />
                  </div>
                </div>
              </Link>
              <Link
                href="/reports"
                prefetch={true}
                className="col-span-12 md:col-span-4 p-6 border border-white/20 rounded-xl hover:border-white/40 hover:scale-105 transition-all duration-300 group"
              >
                <div className="flex items-center justify-between h-full">
                  <div>
                    <h3 className="font-bold text-white text-lg group-hover:text-purple-300 transition-colors tracking-wide">
                      View Reports
                    </h3>
                    <p className="text-purple-200 text-sm mt-2 font-medium tracking-wide">
                      Check performance analytics
                    </p>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white group-hover:scale-110 transition-transform duration-200 shadow-lg shadow-purple-500/30">
                    <FileText className="h-6 w-6" />
                  </div>
                </div>
              </Link>
            </div>
          </div>
        </GlassCard>

        {/* Additional Stats Row - 12-column grid */}
        <div className="grid grid-cols-12 gap-6">
          <GlassCard className="col-span-12 md:col-span-4">
            <div className="p-6">
              <p className="text-purple-200 text-sm font-bold tracking-wide mb-4">
                Active Users
              </p>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-3xl font-bold tracking-tight">1,234</p>
                  <p className="text-green-400 text-sm font-bold tracking-wide">+12.5% this month</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg text-white shadow-lg shadow-blue-500/30">
                  <Users className="h-6 w-6" />
                </div>
              </div>
            </div>
          </GlassCard>
          
          <GlassCard className="col-span-12 md:col-span-4">
            <div className="p-6">
              <p className="text-purple-200 text-sm font-bold tracking-wide mb-4">
                System Uptime
              </p>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-3xl font-bold tracking-tight">99.9%</p>
                  <p className="text-green-400 text-sm font-bold tracking-wide">Excellent</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white shadow-lg shadow-green-500/30">
                  <Shield className="h-6 w-6" />
                </div>
              </div>
            </div>
          </GlassCard>
          
          <GlassCard className="col-span-12 md:col-span-4">
            <div className="p-6">
              <p className="text-purple-200 text-sm font-bold tracking-wide mb-4">
                AI Signals Today
              </p>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-3xl font-bold tracking-tight">156</p>
                  <p className="text-blue-400 text-sm font-bold tracking-wide">High activity</p>
                </div>
                <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white shadow-lg shadow-purple-500/30">
                  <Zap className="h-6 w-6" />
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </>
  );
}