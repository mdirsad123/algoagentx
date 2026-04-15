"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronUp, Eye, Download, Filter, Calendar, TrendingUp, TrendingDown, Clock, Play, X, Search, ChevronLeft, ChevronRight } from "lucide-react";
import EmptyState from "@/components/shared/empty-state";
import axios from "@/lib/axios";
import Toast from "@/components/shared/swal-toast";
import { PageHeader } from "@/components/ui/page-header";
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardDescription, StandardCardContent } from "@/components/ui/standard-card";
import { CardSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton";

interface BacktestHistoryItem {
  id: string;
  strategy_id: string;
  strategy_name: string;
  instrument_id: number;
  instrument_symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number | null;
  net_profit: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  win_rate: number | null;
  total_trades: number | null;
  winning_trades: number | null;
  losing_trades: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Strategy {
  id: string;
  name: string;
}

interface Instrument {
  id: number;
  symbol: string;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

const unwrapApiData = (payload: any) => payload?.success ? payload.data : payload;

export default function BacktestHistoryPage() {
  // Filter state
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [selectedInstrument, setSelectedInstrument] = useState<string>("");
  const [timeframe, setTimeframe] = useState<string>("");
  const [startDateFrom, setStartDateFrom] = useState<string>("");
  const [startDateTo, setStartDateTo] = useState<string>("");
  const [minProfit, setMinProfit] = useState<string>("");
  const [maxDrawdown, setMaxDrawdown] = useState<string>("");
  const [filtersOpen, setFiltersOpen] = useState(true);

  // Quick filters
  const [quickFilter, setQuickFilter] = useState<string>("");

  // Data state
  const [backtests, setBacktests] = useState<BacktestHistoryItem[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedBacktest, setSelectedBacktest] = useState<BacktestHistoryItem | null>(null);

  // Load strategies and instruments on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [strategiesRes, instrumentsRes] = await Promise.all([
          axios.get("/api/v1/strategies"),
          axios.get("/api/v1/instruments")
        ]);
        setStrategies(unwrapApiData(strategiesRes.data));
        setInstruments(unwrapApiData(instrumentsRes.data));
      } catch (error: any) {
        Toast.fire({
          icon: 'error',
          title: 'Failed to load data',
          text: error.response?.data?.detail || 'Unable to load strategies and instruments'
        });
      }
    };
    loadData();
  }, []);

  // Load backtest history
  const loadBacktestHistory = async (page: number = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedStrategy) params.append('strategy_id', selectedStrategy);
      if (selectedInstrument) params.append('instrument_id', selectedInstrument);
      if (timeframe) params.append('timeframe', timeframe);
      if (startDateFrom) params.append('start_date_from', startDateFrom);
      if (startDateTo) params.append('start_date_to', startDateTo);
      if (minProfit) params.append('min_profit', minProfit);
      if (maxDrawdown) params.append('max_drawdown', maxDrawdown);
      params.append('page', page.toString());
      params.append('page_size', '20');

      const response = await axios.get(`/api/v1/backtests/history?${params}`);
      const data = unwrapApiData(response.data);

      setBacktests(data.backtests);
      setPagination(data.pagination);
    } catch (error: any) {
      Toast.fire({
        icon: 'error',
        title: 'Failed to load history',
        text: error.response?.data?.detail || 'Unable to load backtest history'
      });
    } finally {
      setLoading(false);
    }
  };

  // Load initial data
  useEffect(() => {
    loadBacktestHistory();
  }, []);

  const applyFilters = () => {
    loadBacktestHistory(1);
  };

  const clearFilters = () => {
    setSelectedStrategy("");
    setSelectedInstrument("");
    setTimeframe("");
    setStartDateFrom("");
    setStartDateTo("");
    setMinProfit("");
    setMaxDrawdown("");
    setQuickFilter("");
    loadBacktestHistory(1);
  };

  const setQuickDateFilter = (days: number) => {
    setQuickFilter(`${days}D`);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);
    
    setStartDateFrom(startDate.toISOString().split('T')[0]);
    setStartDateTo(endDate.toISOString().split('T')[0]);
    loadBacktestHistory(1);
  };

  const viewBacktestReport = (backtest: BacktestHistoryItem) => {
    setSelectedBacktest(backtest);
  };

  const downloadReport = (backtest: BacktestHistoryItem) => {
    // In a real implementation, this would download the actual report
    Toast.fire({
      icon: 'info',
      title: 'Download',
      text: `Downloading report for ${backtest.strategy_name} - ${backtest.instrument_symbol}`
    });
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return "-";
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return "-";
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'bg-green-500/30 text-green-400 border-green-500/50';
      case 'running': return 'bg-blue-500/30 text-blue-400 border-blue-500/50';
      case 'failed': return 'bg-red-500/30 text-red-400 border-red-500/50';
      case 'pending': return 'bg-yellow-500/30 text-yellow-400 border-yellow-500/50';
      default: return 'bg-gray-500/30 text-gray-400 border-gray-500/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return <TrendingUp className="w-4 h-4" />;
      case 'running': return <Play className="w-4 h-4" />;
      case 'failed': return <TrendingDown className="w-4 h-4" />;
      case 'pending': return <Clock className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1a0f2e] via-[#2a1458] to-[#0f172a]">
      <div className="p-6 space-y-6">
      <PageHeader 
        title="Backtest History"
        subtitle="Review and analyze your completed backtest results"
      />

      {/* Quick Filters */}
      <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
        <CardHeader>
          <CardTitle className="text-white">Quick Filters</CardTitle>
          <CardDescription className="text-gray-400">
            Filter by time period for quick analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Today', value: '1D', days: 1 },
              { label: 'Last 7 Days', value: '7D', days: 7 },
              { label: 'Last 30 Days', value: '30D', days: 30 }
            ].map((filter) => (
              <Button
                key={filter.value}
                variant={quickFilter === filter.value ? "default" : "outline"}
                size="sm"
                onClick={() => setQuickDateFilter(filter.days)}
                className={`px-3 py-1.5 text-sm font-medium rounded-full border transition-all ${
                  quickFilter === filter.value 
                    ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white border-transparent shadow-lg' 
                    : 'bg-white/10 text-gray-300 hover:bg-white/20 border-white/20'
                }`}
              >
                {filter.label}
              </Button>
            ))}
            <Button
              variant={quickFilter === "" ? "default" : "outline"}
              size="sm"
              onClick={clearFilters}
              className={`px-3 py-1.5 text-sm font-medium rounded-full border transition-all ${
                quickFilter === "" 
                  ? 'bg-gray-600/50 text-white border-transparent' 
                  : 'bg-white/10 text-gray-300 hover:bg-white/20 border-white/20'
              }`}
            >
              Clear All
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Filters */}
      <StandardCard className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
        <StandardCardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <StandardCardTitle className="text-white flex items-center gap-2">
              <Filter className="w-5 h-5 text-purple-400" />
              Advanced Filters
            </StandardCardTitle>
            <StandardCardDescription className="text-gray-400">
              Refine your search with detailed criteria
            </StandardCardDescription>
          </div>
          <Collapsible open={filtersOpen} onOpenChange={setFiltersOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white hover:bg-white/10">
                {filtersOpen ? (
                  <ChevronUp className="w-5 h-5" />
                ) : (
                  <ChevronDown className="w-5 h-5" />
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <StandardCardContent className="space-y-4 pt-4">
                {/* First Row: Strategy, Instrument, Timeframe, Min Profit */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Strategy Filter */}
                  <div className="space-y-2">
                    <Label htmlFor="strategy" className="text-gray-300">Strategy</Label>
                    <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                      <SelectTrigger className="bg-white/10 border-white/20 text-white hover:border-white/40">
                        <SelectValue placeholder="All strategies" className="text-gray-500" />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1e1b4b] border-white/10">
                        {strategies.map(strategy => (
                          <SelectItem key={strategy.id} value={strategy.id} className="text-white hover:bg-white/10">
                            {strategy.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Instrument Filter */}
                  <div className="space-y-2">
                    <Label htmlFor="instrument" className="text-gray-300">Instrument</Label>
                    <Select value={selectedInstrument} onValueChange={setSelectedInstrument}>
                      <SelectTrigger className="bg-white/10 border-white/20 text-white hover:border-white/40">
                        <SelectValue placeholder="All instruments" className="text-gray-500" />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1e1b4b] border-white/10">
                        {instruments.map(instrument => (
                          <SelectItem key={instrument.id.toString()} value={instrument.id.toString()} className="text-white hover:bg-white/10">
                            {instrument.symbol}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Timeframe Filter */}
                  <div className="space-y-2">
                    <Label htmlFor="timeframe" className="text-gray-300">Timeframe</Label>
                    <Select value={timeframe} onValueChange={setTimeframe}>
                      <SelectTrigger className="bg-white/10 border-white/20 text-white hover:border-white/40">
                        <SelectValue className="text-gray-500" />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1e1b4b] border-white/10">
                        <SelectItem value="5m" className="text-white hover:bg-white/10">5 Minutes</SelectItem>
                        <SelectItem value="15m" className="text-white hover:bg-white/10">15 Minutes</SelectItem>
                        <SelectItem value="1h" className="text-white hover:bg-white/10">1 Hour</SelectItem>
                        <SelectItem value="1d" className="text-white hover:bg-white/10">1 Day</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Min Profit Filter */}
                  <div className="space-y-2">
                    <Label htmlFor="minProfit" className="text-gray-300">Min Profit ($)</Label>
                    <Input
                      id="minProfit"
                      type="number"
                      value={minProfit}
                      onChange={(e) => setMinProfit(e.target.value)}
                      placeholder="0"
                      className="bg-white/10 border-white/20 text-white placeholder-gray-500 focus:border-purple-500"
                    />
                  </div>
                </div>

                {/* Second Row: Date Range, Max Drawdown, Actions */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Start Date From */}
                  <div className="space-y-2">
                    <Label htmlFor="startDateFrom" className="text-gray-300">Start Date From</Label>
                    <Input
                      id="startDateFrom"
                      type="date"
                      value={startDateFrom}
                      onChange={(e) => setStartDateFrom(e.target.value)}
                      className="bg-white/10 border-white/20 text-white focus:border-purple-500"
                    />
                  </div>

                  {/* Start Date To */}
                  <div className="space-y-2">
                    <Label htmlFor="startDateTo" className="text-gray-300">Start Date To</Label>
                    <Input
                      id="startDateTo"
                      type="date"
                      value={startDateTo}
                      onChange={(e) => setStartDateTo(e.target.value)}
                      className="bg-white/10 border-white/20 text-white focus:border-purple-500"
                    />
                  </div>

                  {/* Max Drawdown Filter */}
                  <div className="space-y-2">
                    <Label htmlFor="maxDrawdown" className="text-gray-300">Max Drawdown (%)</Label>
                    <Input
                      id="maxDrawdown"
                      type="number"
                      value={maxDrawdown}
                      onChange={(e) => setMaxDrawdown(e.target.value)}
                      placeholder="20"
                      className="bg-white/10 border-white/20 text-white placeholder-gray-500 focus:border-purple-500"
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 pt-6">
                    <div className="flex gap-2">
                      <Button 
                        onClick={applyFilters} 
                        disabled={loading}
                        className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white flex-1 shadow-lg"
                      >
                        <Search className="w-4 h-4 mr-2" />
                        Apply Filters
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={clearFilters} 
                        disabled={loading}
                        className="border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                      >
                        Reset
                      </Button>
                    </div>
                  </div>
                </div>
              </StandardCardContent>
            </CollapsibleContent>
          </Collapsible>
        </StandardCardHeader>
      </StandardCard>

      {/* Results Table */}
      <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Backtest Results</CardTitle>
              <CardDescription className="text-gray-400">
                Comprehensive view of all your backtest executions
              </CardDescription>
            </div>
            {pagination && (
              <div className="text-sm text-gray-400">
                Showing {((pagination.page - 1) * pagination.page_size) + 1} to {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of {pagination.total_count} results
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
                <div className="h-10 bg-white/10 rounded animate-pulse"></div>
              </div>
              <div className="h-96 bg-white/10 rounded animate-pulse"></div>
            </div>
          ) : backtests.length === 0 ? (
            <EmptyState
              title="No Backtest Results Yet"
              description="Your backtest history will appear here once you run your first backtest"
              icon={<Play className="w-12 h-12 text-purple-500" />}
              actionLabel="Run Your First Backtest"
              onAction={() => window.location.href = '/backtest'}
              secondaryActionLabel="Browse Strategies"
              secondaryActionHref="/strategies"
            />
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border border-white/10 bg-white/5">
                <Table className="min-w-[1200px]">
                  <TableHeader>
                    <TableRow className="border-white/10">
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Strategy</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Instrument</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Timeframe</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Period</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider text-right">Net Profit</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider text-right">Win Rate</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider text-right">Max DD</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider text-right">Trades</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Status</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Date</TableHead>
                      <TableHead className="text-gray-400 font-semibold text-sm uppercase tracking-wider">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backtests.map((backtest) => (
                      <TableRow 
                        key={backtest.id} 
                        className="border-white/10 hover:bg-white/5 transition-colors"
                      >
                        <TableCell className="font-medium text-white py-4">{backtest.strategy_name}</TableCell>
                        <TableCell className="text-gray-400 py-4">{backtest.instrument_symbol}</TableCell>
                        <TableCell className="text-gray-400 py-4">{backtest.timeframe}</TableCell>
                        <TableCell className="text-gray-400 py-4">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4 text-gray-500" />
                            {formatDate(backtest.start_date)} - {formatDate(backtest.end_date)}
                          </div>
                        </TableCell>
                        <TableCell className={`text-right font-medium py-4 ${
                          backtest.net_profit && backtest.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {formatCurrency(backtest.net_profit)}
                        </TableCell>
                        <TableCell className="text-right text-gray-400 py-4">{formatPercent(backtest.win_rate)}</TableCell>
                        <TableCell className="text-right text-red-400 py-4">{formatPercent(backtest.max_drawdown)}</TableCell>
                        <TableCell className="text-right text-gray-400 py-4">{backtest.total_trades || 0}</TableCell>
                        <TableCell className="py-4">
                          <Badge 
                            variant="outline" 
                            className={`px-2 py-1 text-xs font-medium rounded-full border ${
                              getStatusColor(backtest.status)
                            }`}
                          >
                            <div className="flex items-center gap-1">
                              {getStatusIcon(backtest.status)}
                              <span className="capitalize">{backtest.status}</span>
                            </div>
                          </Badge>
                        </TableCell>
                        <TableCell className="text-gray-400 py-4">{formatDate(backtest.created_at)}</TableCell>
                        <TableCell className="py-4">
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => viewBacktestReport(backtest)}
                              className="flex items-center gap-1 border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                            >
                              <Eye className="w-4 h-4" />
                              View
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => downloadReport(backtest)}
                              className="flex items-center gap-1 border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                            >
                              <Download className="w-4 h-4" />
                              Download
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {pagination && pagination.total_pages > 1 && (
                <div className="flex items-center justify-between mt-6">
                  <div className="text-sm text-gray-400">
                    Page {pagination.page} of {pagination.total_pages} • {pagination.total_count} total results
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => loadBacktestHistory(pagination.page - 1)}
                      disabled={pagination.page <= 1 || loading}
                      className="border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                    >
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => loadBacktestHistory(pagination.page + 1)}
                      disabled={pagination.page >= pagination.total_pages || loading}
                      className="border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                    >
                      Next
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Selected Backtest Details Modal */}
      {selectedBacktest && (
        <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-white text-lg">
                Backtest Report: {selectedBacktest.strategy_name} - {selectedBacktest.instrument_symbol}
              </CardTitle>
              <CardDescription className="text-gray-400">
                Detailed performance metrics and analysis
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedBacktest(null)}
              className="text-gray-400 hover:text-white hover:bg-white/10"
            >
              <X className="w-5 h-5" />
            </Button>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-gradient-to-r from-green-900/40 to-emerald-900/40 border border-green-500/30 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-green-400 font-medium">Net Profit</div>
                    <div className={`text-xl font-bold ${
                      selectedBacktest.net_profit && selectedBacktest.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatCurrency(selectedBacktest.net_profit)}
                    </div>
                  </div>
                  <TrendingUp className="w-8 h-8 text-green-500" />
                </div>
              </div>
              <div className="bg-gradient-to-r from-blue-900/40 to-cyan-900/40 border border-blue-500/30 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-blue-400 font-medium">Win Rate</div>
                    <div className="text-xl font-bold text-blue-400">
                      {formatPercent(selectedBacktest.win_rate)}
                    </div>
                  </div>
                  <TrendingUp className="w-8 h-8 text-blue-500" />
                </div>
              </div>
              <div className="bg-gradient-to-r from-red-900/40 to-orange-900/40 border border-red-500/30 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-red-400 font-medium">Max Drawdown</div>
                    <div className="text-xl font-bold text-red-400">
                      {formatPercent(selectedBacktest.max_drawdown)}
                    </div>
                  </div>
                  <TrendingDown className="w-8 h-8 text-red-500" />
                </div>
              </div>
              <div className="bg-gradient-to-r from-purple-900/40 to-pink-900/40 border border-purple-500/30 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-purple-400 font-medium">Total Trades</div>
                    <div className="text-xl font-bold text-purple-400">
                      {selectedBacktest.total_trades || 0}
                    </div>
                  </div>
                  <Play className="w-8 h-8 text-purple-500" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-semibold text-white">Backtest Details</h4>
                <div className="space-y-2 text-sm text-gray-400">
                  <div className="flex justify-between">
                    <span>Period:</span>
                    <span className="font-medium text-white">{formatDate(selectedBacktest.start_date)} - {formatDate(selectedBacktest.end_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Timeframe:</span>
                    <span className="font-medium text-white">{selectedBacktest.timeframe}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Initial Capital:</span>
                    <span className="font-medium text-white">{formatCurrency(selectedBacktest.initial_capital)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Final Capital:</span>
                    <span className="font-medium text-white">{formatCurrency(selectedBacktest.final_capital)}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <h4 className="font-semibold text-white">Performance Metrics</h4>
                <div className="space-y-2 text-sm text-gray-400">
                  <div className="flex justify-between">
                    <span>Sharpe Ratio:</span>
                    <span className="font-medium text-white">{selectedBacktest.sharpe_ratio?.toFixed(2) || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Winning Trades:</span>
                    <span className="font-medium text-white">{selectedBacktest.winning_trades || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Losing Trades:</span>
                    <span className="font-medium text-white">{selectedBacktest.losing_trades || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="font-medium text-white capitalize">{selectedBacktest.status}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button 
                onClick={() => setSelectedBacktest(null)}
                className="bg-gray-600/50 hover:bg-gray-600 text-white border-white/20"
              >
                Close Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      </div>
    </div>
  );
}