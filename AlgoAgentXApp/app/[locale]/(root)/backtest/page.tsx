"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import axios from "@/lib/axios";
import Toast from "@/components/shared/toast";
import { Play, Loader2, TrendingUp, TrendingDown, DollarSign, Gauge, Eye, RefreshCw, CreditCard } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui/page-header";
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardDescription, StandardCardContent } from "@/components/ui/standard-card";
import { CardSkeleton, TableSkeleton, StatsSkeleton } from "@/components/ui/loading-skeleton";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  XAxis,
  YAxis,
  Tooltip,
  Line,
} from "recharts";

interface Strategy {
  id: string;
  name: string;
}

interface Instrument {
  id: number;
  symbol: string;
}

interface BacktestResponse {
  backtest_id?: string;
  strategy_name: string;
  instrument_symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  net_profit: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  trades: Array<{
    entry_time: string;
    exit_time: string | null;
    side: string;
    quantity: number;
    entry_price: number;
    exit_price: number | null;
    pnl: number | null;
    exit_type: string | null;
  }>;
  equity_curve: Array<{
    timestamp: string;
    equity: number;
  }>;
  saved: boolean;
}

interface JobStatus {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  message: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  job_data?: any;
  result_data?: BacktestResponse;
}

interface MarketDataRange {
  min_timestamp: string;
  max_timestamp: string;
  candle_count: number;
}

export default function BacktestPage() {
  // Form state
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [selectedInstrument, setSelectedInstrument] = useState<string>("");
  const [timeframe, setTimeframe] = useState<string>("1d");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [capital, setCapital] = useState<string>("100000");

  // Job state
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // UI state
  const [loading, setLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(null);

  // Progress tracking
  const [showProgress, setShowProgress] = useState(false);

  // Credit system state
  const [userBalance, setUserBalance] = useState<number | null>(null);
  const [estimatedCost, setEstimatedCost] = useState<number | null>(null);
  const [costLoading, setCostLoading] = useState(false);
  const [insufficientCredits, setInsufficientCredits] = useState(false);

  // Load strategies, instruments, and credit balance on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [strategiesRes, instrumentsRes, balanceRes] = await Promise.all([
          axios.get("/api/v1/strategies"),
          axios.get("/api/v1/instruments"),
          axios.get("/api/v1/credits/balance")
        ]);
        setStrategies(strategiesRes.data);
        setInstruments(instrumentsRes.data);
        setUserBalance(balanceRes.data.balance);
      } catch (error: any) {
        Toast.fire({
          icon: 'error',
          title: 'Failed to load data',
          text: error.response?.data?.detail || 'Unable to load strategies, instruments, or credit balance'
        });
      }
    };
    loadData();
  }, []);

  // Handle query parameters to prefill symbol
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const symbol = urlParams.get('symbol');
    
    if (symbol && instruments.length > 0) {
      const matchingInstrument = instruments.find(instr => instr.symbol === symbol);
      if (matchingInstrument) {
        setSelectedInstrument(matchingInstrument.id.toString());
      }
    }
  }, [instruments]);

  // Watch for changes in form fields to update cost preview
  useEffect(() => {
    if (startDate && endDate && timeframe) {
      calculateCostPreview();
    }
  }, [startDate, endDate, timeframe, userBalance]);

  // Poll job status
  const pollJobStatus = async (jobId: string) => {
    try {
      const response = await axios.get(`/api/v1/jobs/${jobId}`);
      const jobStatus: JobStatus = response.data;

      setCurrentJob(jobStatus);

      if (jobStatus.status === 'completed' && jobStatus.result_data) {
        // Job completed successfully
        setBacktestResult(jobStatus.result_data);
        setCurrentJob(null);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }

        // Update balance after successful backtest
        try {
          const balanceRes = await axios.get("/api/v1/credits/balance");
          setUserBalance(balanceRes.data.balance);
        } catch (error) {
          console.error('Failed to update balance after backtest:', error);
        }

        Toast.fire({
          icon: 'success',
          title: 'Backtest completed',
          text: `Strategy: ${jobStatus.result_data.strategy_name} | Net P&L: $${jobStatus.result_data.net_profit.toFixed(2)}`
        });

      } else if (jobStatus.status === 'failed') {
        // Job failed
        setCurrentJob(null);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }

        Toast.fire({
          icon: 'error',
          title: 'Backtest failed',
          text: jobStatus.message || 'An error occurred during backtesting'
        });
      }
      // Continue polling for 'pending', 'running', 'retry' statuses

    } catch (error: any) {
      console.error('Error polling job status:', error);
      // Stop polling on error
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      
      Toast.fire({
        icon: 'error',
        title: 'Polling failed',
        text: 'Unable to fetch job status. Please check your connection.'
      });
    }
  };

  const previewData = async () => {
    if (!selectedInstrument || !timeframe) {
      Toast.fire({
        icon: 'warning',
        title: 'Missing fields',
        text: 'Please select an instrument and timeframe to preview data'
      });
      return;
    }

    try {
      const response = await axios.get("/api/v1/market-data/range", {
        params: {
          instrument_id: selectedInstrument,
          timeframe: timeframe
        }
      });
      
      const dataRange: MarketDataRange = response.data;
      
      // Auto-fill date range
      const minDate = new Date(dataRange.min_timestamp).toISOString().split('T')[0];
      const maxDate = new Date(dataRange.max_timestamp).toISOString().split('T')[0];
      
      setStartDate(minDate);
      setEndDate(maxDate);

      Toast.fire({
        icon: 'success',
        title: 'Data preview loaded',
        text: `Available data: ${dataRange.candle_count} candles from ${minDate} to ${maxDate}`
      });

      // Calculate cost preview after setting dates
      await calculateCostPreview(minDate, maxDate, timeframe);

    } catch (error: any) {
      Toast.fire({
        icon: 'error',
        title: 'Failed to preview data',
        text: error.response?.data?.detail || 'Unable to fetch market data range'
      });
    }
  };

  const calculateCostPreview = async (start?: string, end?: string, tf?: string) => {
    const sDate = start || startDate;
    const eDate = end || endDate;
    const tfValue = tf || timeframe;

    if (!sDate || !eDate || !tfValue) {
      setEstimatedCost(null);
      setInsufficientCredits(false);
      return;
    }

    setCostLoading(true);
    try {
      const response = await axios.post("/api/v1/credits/preview-cost", {
        start_date: sDate,
        end_date: eDate,
        timeframe: tfValue
      });
      
      const cost = response.data.total_cost;
      setEstimatedCost(cost);
      setInsufficientCredits(userBalance !== null && cost > userBalance);
    } catch (error: any) {
      console.error('Error calculating cost preview:', error);
      setEstimatedCost(null);
      setInsufficientCredits(false);
    } finally {
      setCostLoading(false);
    }
  };

  const runBacktest = async () => {
    if (!selectedStrategy || !selectedInstrument || !timeframe || !startDate || !endDate || !capital) {
      Toast.fire({
        icon: 'warning',
        title: 'Missing fields',
        text: 'Please fill in all required fields'
      });
      return;
    }

    setLoading(true);
    setCurrentJob(null);
    setBacktestResult(null);

    try {
      const payload = {
        strategy_id: selectedStrategy,
        instrument_id: parseInt(selectedInstrument),
        timeframe,
        start_date: startDate,
        end_date: endDate,
        capital: parseFloat(capital),
        save_result: true
      };

      const response = await axios.post("/api/v1/backtests/run", payload);
      const jobResponse = response.data;

      // Start polling job status
      const jobId = jobResponse.job_id;
      const interval = setInterval(() => pollJobStatus(jobId), 2000); // Poll every 2 seconds
      setPollingInterval(interval);

      // Initial poll
      await pollJobStatus(jobId);

      Toast.fire({
        icon: 'info',
        title: 'Backtest started',
        text: 'Processing in background...'
      });

    } catch (error: any) {
      setLoading(false);
      Toast.fire({
        icon: 'error',
        title: 'Failed to start backtest',
        text: error.response?.data?.detail || 'An error occurred while starting the backtest'
      });
    } finally {
      setLoading(false);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Prepare chart data
  const winLossData = backtestResult ? [
    { name: "Wins", value: Math.round(backtestResult.total_trades * backtestResult.win_rate) },
    { name: "Losses", value: Math.round(backtestResult.total_trades * (1 - backtestResult.win_rate)) },
  ] : [];

  const equityData = backtestResult?.equity_curve.map(point => ({
    date: new Date(point.timestamp).toLocaleDateString(),
    equity: Number(point.equity)
  })) || [];

  const COLORS = ["#22c55e", "#ef4444"]; // Green for wins, red for losses

  // Progress step labels
  const getProgressSteps = () => {
    if (!currentJob) return [];
    
    const steps = [
      { label: "Initializing backtest", progress: 10 },
      { label: "Fetching market data", progress: 20 },
      { label: "Generating trading signals", progress: 50 },
      { label: "Building trade history", progress: 70 },
      { label: "Calculating performance metrics", progress: 90 },
      { label: "Saving results", progress: 100 }
    ];

    return steps;
  };

  const currentStep = getProgressSteps().find(step => step.progress <= (currentJob?.progress || 0));
  const nextStep = getProgressSteps().find(step => step.progress > (currentJob?.progress || 0));

  const runAgain = () => {
    setBacktestResult(null);
    setCurrentJob(null);
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    // Re-run with same parameters
    runBacktest();
  };

  return (
    <AppShell pageTitle="Backtest">
      <PageHeader 
        title="Backtest Analysis"
        subtitle="Execute and analyze trading strategy performance"
      />

      <div className="space-y-6">
        {/* Credit Balance Section */}
        <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-gray-700" />
              Credit Balance
            </CardTitle>
            <CardDescription className="text-gray-600">
              Your current credit balance and estimated backtest cost
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Current Balance */}
              <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border border-gray-100 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Current Balance</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {userBalance !== null ? userBalance : 'Loading...'}
                    </p>
                  </div>
                  <div className="p-2 bg-blue-500 rounded-full">
                    <CreditCard className="w-6 h-6 text-white" />
                  </div>
                </div>
              </div>

              {/* Estimated Cost */}
              <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-gray-100 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Estimated Cost</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {costLoading ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-5 h-5 animate-spin text-gray-600" />
                          Calculating...
                        </div>
                      ) : estimatedCost !== null ? (
                        estimatedCost
                      ) : (
                        'Select parameters'
                      )}
                    </p>
                  </div>
                  <div className="p-2 bg-green-500 rounded-full">
                    <DollarSign className="w-6 h-6 text-white" />
                  </div>
                </div>
              </div>

              {/* Balance After */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-gray-100 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Balance After</p>
                    <p className={`text-2xl font-bold ${
                      userBalance !== null && estimatedCost !== null && userBalance >= estimatedCost
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      {userBalance !== null && estimatedCost !== null 
                        ? (userBalance - estimatedCost).toFixed(0)
                        : 'Select parameters'
                      }
                    </p>
                  </div>
                  <div className={`p-2 rounded-full ${
                    userBalance !== null && estimatedCost !== null && userBalance >= estimatedCost
                      ? 'bg-green-500'
                      : 'bg-red-500'
                  }`}>
                    <Gauge className="w-6 h-6 text-white" />
                  </div>
                </div>
              </div>
            </div>

            {/* Insufficient Credits Warning */}
            {insufficientCredits && (
              <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                    <div>
                      <p className="text-red-600 font-semibold">Insufficient Credits</p>
                      <p className="text-red-500 text-sm">
                        You need {estimatedCost && userBalance ? (estimatedCost - userBalance) : 0} more credits to run this backtest.
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    className="border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400"
                  >
                    Upgrade Plan
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Form Card - Premium Design */}
        <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Backtest Configuration</CardTitle>
            <CardDescription className="text-gray-600">
              Configure your backtest parameters and run analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              {/* Strategy */}
              <div className="lg:col-span-2 space-y-2">
                <Label htmlFor="strategy" className="text-gray-700">Strategy</Label>
                <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                  <SelectTrigger className="bg-white border-gray-200 text-gray-900 hover:border-gray-300">
                    <SelectValue placeholder="Select strategy" className="text-gray-600" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {strategies.map(strategy => (
                      <SelectItem key={strategy.id} value={strategy.id} className="text-gray-900 hover:bg-gray-100">
                        {strategy.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Instrument */}
              <div className="lg:col-span-2 space-y-2">
                <Label htmlFor="instrument" className="text-gray-700">Instrument</Label>
                <Select value={selectedInstrument} onValueChange={setSelectedInstrument}>
                  <SelectTrigger className="bg-white border-gray-200 text-gray-900 hover:border-gray-300">
                    <SelectValue placeholder="Select instrument" className="text-gray-600" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {instruments.map(instrument => (
                      <SelectItem key={instrument.id.toString()} value={instrument.id.toString()} className="text-gray-900 hover:bg-gray-100">
                        {instrument.symbol}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Timeframe */}
              <div className="space-y-2">
                <Label htmlFor="timeframe" className="text-gray-700">Timeframe</Label>
                <Select value={timeframe} onValueChange={setTimeframe}>
                  <SelectTrigger className="bg-white border-gray-200 text-gray-900 hover:border-gray-300">
                    <SelectValue className="text-gray-600" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    <SelectItem value="5m" className="text-gray-900 hover:bg-gray-100">5 Minutes</SelectItem>
                    <SelectItem value="15m" className="text-gray-900 hover:bg-gray-100">15 Minutes</SelectItem>
                    <SelectItem value="1h" className="text-gray-900 hover:bg-gray-100">1 Hour</SelectItem>
                    <SelectItem value="1d" className="text-gray-900 hover:bg-gray-100">1 Day</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Capital */}
              <div className="space-y-2">
                <Label htmlFor="capital" className="text-gray-700">Initial Capital</Label>
                <Input
                  id="capital"
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                  placeholder="100000"
                  className="bg-white border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate" className="text-gray-700">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-white border-gray-200 text-gray-900 focus:border-blue-500"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate" className="text-gray-700">End Date</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-white border-gray-200 text-gray-900 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Preview and Run Buttons */}
            <div className="flex items-center gap-4">
              <Button
                onClick={previewData}
                variant="outline"
                className="flex items-center gap-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
              >
                <Eye className="w-4 h-4 text-gray-600" />
                Preview Data
              </Button>
              
              <Button
                onClick={runBacktest}
                disabled={loading || !!currentJob || insufficientCredits}
                className={`flex items-center gap-3 px-8 py-3 text-lg font-semibold ${
                  insufficientCredits 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed hover:bg-gray-300' 
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {(loading || currentJob) ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
                {currentJob ? 'Processing...' : loading ? 'Starting...' : insufficientCredits ? 'Insufficient Credits' : 'Run Backtest'}
              </Button>

              {currentJob && (
                <div className="flex-1 max-w-md space-y-2">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Progress</span>
                    <span>{currentJob.progress}%</span>
                  </div>
                  <Progress value={currentJob.progress} className="w-full h-2 bg-gray-200" />
                  <p className="text-sm text-gray-500">
                    {currentJob.message}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Progress Section */}
        {currentJob && (
          <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
            <CardHeader>
              <CardTitle className="text-gray-900">Backtest Progress</CardTitle>
              <CardDescription className="text-gray-600">
                Current step: {currentStep?.label || currentJob.message}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Overall Progress</span>
                    <span>{currentJob.progress}%</span>
                  </div>
                  <Progress value={currentJob.progress} className="w-full h-3 bg-gray-200" />
                  <p className="text-sm text-gray-500">{currentJob.message}</p>
                </div>

                {/* Step-by-Step Progress */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-gray-600">Execution Steps:</h4>
                  {getProgressSteps().map((step, index) => (
                    <div key={index} className="flex items-center space-x-4">
                      <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                        step.progress <= (currentJob.progress || 0) 
                          ? 'bg-green-500' 
                          : 'bg-gray-300'
                      }`}>
                        {step.progress <= (currentJob.progress || 0) && (
                          <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <div className="flex-1">
                        <p className={`text-sm font-medium ${
                          step.progress <= (currentJob.progress || 0) 
                            ? 'text-green-600' 
                            : 'text-gray-500'
                        }`}>
                          {step.label}
                        </p>
                      </div>
                      <div className={`text-xs font-semibold ${
                        step.progress <= (currentJob.progress || 0) 
                          ? 'text-green-600' 
                          : 'text-gray-400'
                      }`}>
                        {step.progress}%
                      </div>
                    </div>
                  ))}
                </div>

                {/* Estimated Time */}
                <div className="text-xs text-gray-500">
                  Estimated time: 30 seconds to 2 minutes depending on data range
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {backtestResult && (
          <>
            {/* Run Again Button */}
            <div className="flex justify-end">
              <Button
                onClick={runAgain}
                variant="outline"
                className="flex items-center gap-2 border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
              >
                <RefreshCw className="w-4 h-4 text-gray-600" />
                Run Again
              </Button>
            </div>

            {/* Metrics Cards - Premium KPI Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="hover:shadow-xl hover:shadow-green-500/10 transition-all duration-300 border-gray-200">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardDescription className="text-gray-600 text-sm font-medium">Net Profit</CardDescription>
                    <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
                      ${backtestResult.net_profit.toFixed(2)}
                    </CardTitle>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                    <DollarSign className="h-6 w-6 text-white" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className={`text-sm font-medium ${
                    backtestResult.net_profit >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {backtestResult.net_profit >= 0 ? 'Profitable' : 'Loss'}
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardDescription className="text-gray-600 text-sm font-medium">Win Rate</CardDescription>
                    <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
                      {(backtestResult.win_rate * 100).toFixed(1)}%
                    </CardTitle>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                    <Gauge className="h-6 w-6 text-white" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">Success rate</p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-xl hover:shadow-red-500/10 transition-all duration-300 border-gray-200">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardDescription className="text-gray-600 text-sm font-medium">Max Drawdown</CardDescription>
                    <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
                      {(backtestResult.max_drawdown * 100).toFixed(2)}%
                    </CardTitle>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                    <TrendingDown className="h-6 w-6 text-white" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">Risk metric</p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-gray-200">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div>
                    <CardDescription className="text-gray-600 text-sm font-medium">Sharpe Ratio</CardDescription>
                    <CardTitle className="text-2xl font-bold tracking-tight text-gray-900">
                      {backtestResult.sharpe_ratio.toFixed(2)}
                    </CardTitle>
                  </div>
                  <div className="p-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-white" />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">Risk-adjusted return</p>
                </CardContent>
              </Card>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Win/Loss Pie Chart */}
              <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
                <CardHeader>
                  <CardTitle className="text-gray-900">Win/Loss Distribution</CardTitle>
                  <CardDescription className="text-gray-600">
                    Trade outcome analysis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                      <Pie
                        data={winLossData}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={110}
                        dataKey="value"
                        label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(1)}%)`}
                        labelLine={false}
                      >
                        {winLossData.map((_, index) => (
                          <Cell key={index} fill={COLORS[index]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        formatter={(value, name) => [`${value} trades`, name]}
                        contentStyle={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e5e7eb',
                          color: '#1f2937'
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Equity Curve */}
              <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
                <CardHeader>
                  <CardTitle className="text-gray-900">Equity Curve</CardTitle>
                  <CardDescription className="text-gray-600">
                    Portfolio value over time
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={equityData}>
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: '#6b7280' }}
                        axisLine={{ stroke: '#e5e7eb' }}
                        tickLine={{ stroke: '#e5e7eb' }}
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: '#6b7280' }}
                        axisLine={{ stroke: '#e5e7eb' }}
                        tickLine={{ stroke: '#e5e7eb' }}
                      />
                      <Tooltip 
                        formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Equity']}
                        contentStyle={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e5e7eb',
                          color: '#1f2937'
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke="#60a5fa"
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6, stroke: '#60a5fa', strokeWidth: 2, fill: '#ffffff' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Trade History Table */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Trade History</CardTitle>
                <CardDescription className="text-gray-600">
                  Detailed trade execution log
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-gray-100">
                        <TableHead className="text-gray-600">Entry Time</TableHead>
                        <TableHead className="text-gray-600">Exit Time</TableHead>
                        <TableHead className="text-gray-600">Side</TableHead>
                        <TableHead className="text-gray-600">Quantity</TableHead>
                        <TableHead className="text-gray-600">Entry Price</TableHead>
                        <TableHead className="text-gray-600">Exit Price</TableHead>
                        <TableHead className="text-gray-600">P&L</TableHead>
                        <TableHead className="text-gray-600">Result</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {backtestResult.trades.map((trade, index) => (
                        <TableRow key={index} className="border-gray-100 hover:bg-gray-50">
                          <TableCell className="text-gray-900 font-medium">{new Date(trade.entry_time).toLocaleString()}</TableCell>
                          <TableCell className="text-gray-600">
                            {trade.exit_time ? new Date(trade.exit_time).toLocaleString() : '-'}
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              trade.side === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {trade.side}
                            </span>
                          </TableCell>
                          <TableCell className="text-gray-900">{trade.quantity}</TableCell>
                          <TableCell className="text-gray-900 font-medium">${trade.entry_price.toFixed(2)}</TableCell>
                          <TableCell className="text-gray-600">
                            {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
                          </TableCell>
                          <TableCell className={trade.pnl && trade.pnl >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                            {trade.pnl ? `$${trade.pnl.toFixed(2)}` : '-'}
                          </TableCell>
                          <TableCell>
                            {trade.pnl && trade.pnl > 0 ? (
                              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">WIN</span>
                            ) : trade.pnl && trade.pnl < 0 ? (
                              <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-semibold">LOSS</span>
                            ) : (
                              <span className="text-gray-500">PENDING</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                      {backtestResult.trades.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center text-gray-500 py-8">
                            No trades found for this strategy
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}


