"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import DatePicker from "@/components/ui/date-picker";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableHead, TableCell, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { RefreshCw, ExternalLink, Calendar as CalendarIcon, Play, PlayCircle, Lock, AlertCircle, CheckCircle, Clock, X, Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { format } from "date-fns";
import { useTranslation } from "@/hooks/use-translations";
import { toast } from "@/components/ui/use-toast";
import { StatusBar } from "@/components/ai-screener/StatusBar";
import { useUser } from "@/contexts/user-context";

// Import types and API
import { NewsItem, AnnouncementItem } from "@/types/ai-screener";
import { aiScreenerApi } from "@/lib/api/ai-screener";
import { PageHeader } from "@/components/ui/page-header";
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardDescription, StandardCardContent } from "@/components/ui/standard-card";
import { CardSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton";

interface NewsTableProps {
  title: string;
  sentimentType: "positive" | "negative";
  loading: boolean;
  data: NewsItem[];
  onRefresh: () => void;
}

interface AnnouncementsTableProps {
  loading: boolean;
  data: AnnouncementItem[];
  onRefresh: () => void;
}

interface SearchTableProps {
  loading: boolean;
  data: NewsItem[];
  query: string;
  onSearch: (query: string) => void;
  onRefresh: () => void;
}

interface RunScreenerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRun: (mode: string, depth: string) => void;
  isRunning: boolean;
}

interface JobHistoryItem {
  job_id: string;
  status: string;
  mode: string;
  depth: string;
  policy: string;
  cost: number;
  deducted: number;
  policy_message?: string | null;
  remaining_balance?: number | null;
  remaining_included?: number | null;
  created_at: string;
  updated_at: string;
  result: any;
}

const RunScreenerModal: React.FC<RunScreenerModalProps> = ({ isOpen, onClose, onRun, isRunning }) => {
  const [mode, setMode] = useState("basic");
  const [depth, setDepth] = useState("light");

  if (!isOpen) return null;

  const handleRun = () => {
    onRun(mode, depth);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="w-5 h-5" />
            Run AI Screener
          </CardTitle>
          <p className="text-sm text-gray-600">Choose analysis parameters</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="mode">Analysis Mode</Label>
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger>
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic">Basic (Free)</SelectItem>
                <SelectItem value="advanced">Advanced (Premium)</SelectItem>
                <SelectItem value="premium">Premium (Premium)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label htmlFor="depth">Analysis Depth</Label>
            <Select value={depth} onValueChange={setDepth}>
              <SelectTrigger>
                <SelectValue placeholder="Select depth" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="deep">Deep</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Button 
              onClick={handleRun} 
              disabled={isRunning}
              className="flex-1"
            >
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Run Analysis
                </>
              )}
            </Button>
            <Button variant="outline" onClick={onClose} disabled={isRunning}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default function AiScreenerPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("news");
  const [date, setDate] = useState<Date>(new Date());
  const [exchangeFilter, setExchangeFilter] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState<string>("");

  // Run Screener state
  const [showRunModal, setShowRunModal] = useState(false);
  const [isRunningScreener, setIsRunningScreener] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<any>(null);

  // History state
  const [history, setHistory] = useState<JobHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);

  // Plan gating state
  const { user } = useUser();
  const [planCheckLoading, setPlanCheckLoading] = useState(false);

  // Helper function to navigate to backtest page with symbol
  const handleBacktest = (symbol: string) => {
    router.push(`/backtest?symbol=${encodeURIComponent(symbol)}`);
  };

  // Check if user has access to premium features
  const hasPremiumAccess = () => {
    // Use type assertion to safely access plan property
    const userAny = user as any;
    const plan = userAny?.plan || userAny?.plan_code || userAny?.subscription?.plan || "FREE";
    return plan !== "FREE";
  };

  // Check if user can run AI screener based on plan
  const canRunAiScreener = (mode: string, depth: string) => {
    const userAny = user as any;
    const plan = userAny?.plan || userAny?.plan_code || userAny?.subscription?.plan || "FREE";
    if (plan === "FREE") {
      return mode === "basic" && depth === "light";
    }
    return true;
  };

  // Run AI Screener with plan gating
  const handleRunAiScreener = async (mode: string, depth: string) => {
    if (!canRunAiScreener(mode, depth)) {
      toast({
        title: "Upgrade Required",
        description: "Advanced AI screener features require a premium subscription. Please upgrade to access these features.",
        variant: "destructive"
      });
      return;
    }

    setIsRunningScreener(true);
    setShowRunModal(false);
    setJobStatus("pending");

    try {
      const response = await aiScreenerApi.runAiScreener(mode, depth);
      setCurrentJobId(response.job_id);
      setJobStatus("accepted");
      toast({
        title: "Analysis Started",
        description: "Your AI screener analysis has been submitted. Results will be available shortly."
      });

      // Start polling for job status
      pollJobStatus(response.job_id);
    } catch (error: any) {
      console.error("Error running AI screener:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to start AI screener";
      const requestId = error.response?.headers?.['x-request-id'] || error.response?.data?.request_id;
      
      toast({
        title: "Error Starting Analysis",
        description: requestId ? `${errorMessage} (Request ID: ${requestId})` : errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsRunningScreener(false);
    }
  };

  // Poll job status until completion
  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        toast({
          title: "Analysis Timeout",
          description: "The analysis is taking longer than expected. Please check the history tab for results.",
          variant: "destructive"
        });
        setJobStatus("timeout");
        return;
      }

      try {
        const statusResponse = await aiScreenerApi.getAiScreenerJobStatus(jobId);
        setJobStatus(statusResponse.status);

        if (statusResponse.status === "COMPLETED") {
          setJobResult(statusResponse.result);
          toast({
            title: "Analysis Complete",
            description: "Your AI screener analysis is ready!"
          });
          fetchHistory();
          return;
        } else if (statusResponse.status === "FAILED") {
          toast({
            title: "Analysis Failed",
            description: statusResponse.result?.error || "The analysis failed. Please try again.",
            variant: "destructive"
          });
          return;
        } else if (statusResponse.status === "RUNNING") {
          setJobStatus("running");
        }

        attempts++;
        setTimeout(poll, 5000); // Poll every 5 seconds
      } catch (error) {
        console.error("Error polling job status:", error);
        toast({
          title: "Connection Error",
          description: "Unable to check analysis status. Please check the history tab.",
          variant: "destructive"
        });
      }
    };

    poll();
  };

  // Fetch job history
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await aiScreenerApi.getAiScreenerHistory(
        undefined, undefined, undefined, undefined, undefined,
        "created_at", "desc", historyPage, 10
      );
      setHistory(response.jobs);
    } catch (error) {
      console.error("Error fetching history:", error);
      toast({
        title: "Error",
        description: "Failed to fetch job history",
        variant: "destructive"
      });
    } finally {
      setHistoryLoading(false);
    }
  };

  // View job details
  const handleViewJobDetails = (job: JobHistoryItem) => {
    if (job.result && job.status === "COMPLETED") {
      // Navigate to a detailed view or show modal with results
      toast({
        title: "Job Details",
        description: `Mode: ${job.mode}, Depth: ${job.depth}, Status: ${job.status}`
      });
    }
  };

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch news data
  const fetchNewsData = async () => {
    setPlanCheckLoading(true);
    try {
      const dateStr = format(date, "yyyy-MM-dd");
      
      const [positiveRes, negativeRes] = await Promise.all([
        aiScreenerApi.getTopPositiveNews(dateStr, 10),
        aiScreenerApi.getTopNegativeNews(dateStr, 10)
      ]);
      
      setPositiveNews(positiveRes.items);
      setNegativeNews(negativeRes.items);
    } catch (error) {
      console.error("Error fetching news:", error);
      toast({
        title: "Error",
        description: "Failed to fetch news data",
        variant: "destructive"
      });
    } finally {
      setPlanCheckLoading(false);
    }
  };

  // Fetch announcements data
  const fetchAnnouncementsData = async () => {
    setPlanCheckLoading(true);
    try {
      const dateStr = format(date, "yyyy-MM-dd");
      const res = await aiScreenerApi.getLatestAnnouncements(dateStr, 50);
      setAnnouncements(res.items);
    } catch (error) {
      console.error("Error fetching announcements:", error);
      toast({
        title: "Error",
        description: "Failed to fetch announcements",
        variant: "destructive"
      });
    } finally {
      setPlanCheckLoading(false);
    }
  };

  // Fetch search data
  const fetchSearchData = async (query: string) => {
    if (!query.trim()) return;
    
    setPlanCheckLoading(true);
    try {
      const dateStr = format(date, "yyyy-MM-dd");
      const res = await aiScreenerApi.searchNews(query, dateStr);
      setSearchResults(res.items);
    } catch (error) {
      console.error("Error fetching search results:", error);
      toast({
        title: "Error",
        description: "Failed to fetch search results",
        variant: "destructive"
      });
    } finally {
      setPlanCheckLoading(false);
    }
  };

  // Initial data fetch
  useEffect(() => {
    fetchNewsData();
    fetchAnnouncementsData();
    fetchHistory();
  }, [date]);

  // Search data fetch
  useEffect(() => {
    fetchSearchData(debouncedSearchQuery);
  }, [debouncedSearchQuery, date]);

  // State for data
  const [positiveNews, setPositiveNews] = useState<NewsItem[]>([]);
  const [negativeNews, setNegativeNews] = useState<NewsItem[]>([]);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [searchResults, setSearchResults] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [announcementsLoading, setAnnouncementsLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  // Filter announcements by exchange
  const filteredAnnouncements = announcements.filter(item => {
    if (exchangeFilter === "All") return true;
    return item.exchange === exchangeFilter;
  });

  const { t } = useTranslation();

  const NewsTable = ({ title, sentimentType, loading, data, onRefresh }: NewsTableProps) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">{title}</CardTitle>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No {sentimentType} news found for {format(date, "MMM dd, yyyy")}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Sentiment</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    <Badge variant="outline" className="bg-gray-50 text-gray-900 border-gray-200">
                      {item.symbol}
                    </Badge>
                  </TableCell>
                  <TableCell>{format(new Date(item.date), "MMM dd, yyyy")}</TableCell>
                  <TableCell className="max-w-md">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline flex items-center"
                    >
                      <span className="truncate block max-w-xs">{item.title}</span>
                      <ExternalLink className="h-4 w-4 ml-1 flex-shrink-0" />
                    </a>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant={sentimentType === "positive" ? "default" : "secondary"}
                      className={sentimentType === "positive" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}
                    >
                      {sentimentType.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className={sentimentType === "positive" ? "text-green-600" : "text-red-600"}>
                      {item.sentiment_score.toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        View
                      </a>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBacktest(item.symbol)}
                        className="flex items-center gap-2 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
                      >
                        <PlayCircle className="w-4 h-4" />
                        Backtest
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );

  const AnnouncementsTable = ({ loading, data, onRefresh }: AnnouncementsTableProps) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Announcements (NSE/BSE)</CardTitle>
        <div className="flex items-center space-x-4">
          <Select value={exchangeFilter} onValueChange={setExchangeFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by Exchange" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Exchanges</SelectItem>
              <SelectItem value="NSE">NSE</SelectItem>
              <SelectItem value="BSE">BSE</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No announcements found for {format(date, "MMM dd, yyyy")}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Link</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    <Badge variant="outline" className="bg-gray-50 text-gray-900 border-gray-200">
                      {item.symbol}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={item.exchange === "NSE" ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-orange-50 text-orange-700 border-orange-200"}>
                      {item.exchange}
                    </Badge>
                  </TableCell>
                  <TableCell>{format(new Date(item.date), "MMM dd, yyyy")}</TableCell>
                  <TableCell className="max-w-md">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline flex items-center"
                    >
                      <span className="truncate block max-w-xs">{item.title}</span>
                      <ExternalLink className="h-4 w-4 ml-1 flex-shrink-0" />
                    </a>
                  </TableCell>
                  <TableCell>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View
                    </a>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );

  const SearchTable = ({ loading, data, query, onSearch, onRefresh }: SearchTableProps) => (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Search Results</CardTitle>
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <div className="flex-1">
            <Input
              placeholder="Search by symbol or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSearch(searchQuery)}
              disabled={loading || !searchQuery.trim()}
            >
              Search
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {query ? `No results found for "${query}"` : "Enter a search query to get started"}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Summary</TableHead>
                <TableHead>Sentiment</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    <Badge variant="outline" className="bg-gray-50 text-gray-900 border-gray-200">
                      {item.symbol}
                    </Badge>
                  </TableCell>
                  <TableCell>{format(new Date(item.date), "MMM dd, yyyy")}</TableCell>
                  <TableCell className="max-w-md">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline flex items-center"
                    >
                      <span className="truncate block max-w-xs">{item.title}</span>
                      <ExternalLink className="h-4 w-4 ml-1 flex-shrink-0" />
                    </a>
                  </TableCell>
                  <TableCell className="max-w-xs truncate">{item.summary}</TableCell>
                  <TableCell>
                    <Badge 
                      variant={item.sentiment_label === "positive" ? "default" : "secondary"}
                      className={item.sentiment_label === "positive" ? "bg-green-100 text-green-800" : item.sentiment_label === "negative" ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-800"}
                    >
                      {item.sentiment_label.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className={item.sentiment_label === "positive" ? "text-green-600" : item.sentiment_label === "negative" ? "text-red-600" : "text-gray-600"}>
                      {item.sentiment_score.toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        View
                      </a>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleBacktest(item.symbol)}
                        className="flex items-center gap-2 text-gray-700 hover:bg-gray-50 hover:border-gray-300"
                      >
                        <PlayCircle className="w-4 h-4" />
                        Backtest
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );

  const HistoryTable = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Analysis History
        </CardTitle>
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">Recent AI screener analyses</p>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHistory}
            disabled={historyLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${historyLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {historyLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No analysis history found. Run your first AI screener analysis to see results here.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Status</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Depth</TableHead>
                <TableHead>Cost</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.map((job, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Badge 
                      variant={job.status === "COMPLETED" ? "default" : job.status === "RUNNING" ? "secondary" : "destructive"}
                      className={job.status === "COMPLETED" ? "bg-green-100 text-green-800" : job.status === "RUNNING" ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800"}
                    >
                      {job.status === "COMPLETED" ? <CheckCircle className="w-4 h-4 mr-1" /> : job.status === "RUNNING" ? <Clock className="w-4 h-4 mr-1" /> : <X className="w-4 h-4 mr-1" />}
                      {job.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{job.mode}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{job.depth}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">₹{job.cost}</span>
                  </TableCell>
                  <TableCell>
                    {format(new Date(job.created_at), "MMM dd, yyyy HH:mm")}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewJobDetails(job)}
                        disabled={job.status !== "COMPLETED"}
                      >
                        View Details
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );

  const RunScreenerCard = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PlayCircle className="w-5 h-5" />
          Run AI Analysis
        </CardTitle>
        <CardDescription>
          Perform advanced AI analysis on market data. {hasPremiumAccess() ? "Premium features available!" : "Upgrade to access premium features."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {jobStatus === "running" && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-blue-800">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Analysis in progress...</span>
            </div>
            <p className="text-sm text-blue-600 mt-1">Please wait while we process your analysis.</p>
          </div>
        )}
        
        {jobStatus === "completed" && jobResult && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-green-800">
              <CheckCircle className="h-4 w-4" />
              <span>Analysis completed successfully!</span>
            </div>
            <p className="text-sm text-green-600 mt-1">Check the results above or in your history.</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <h4 className="font-semibold">Free Analysis</h4>
            <p className="text-sm text-gray-600">Basic analysis with light depth - available to all users</p>
            <Button 
              onClick={() => handleRunAiScreener("basic", "light")}
              disabled={isRunningScreener}
              className="w-full"
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              Run Basic Analysis
            </Button>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold flex items-center gap-2">
              Premium Analysis
              {!hasPremiumAccess() && <Lock className="w-4 h-4 text-gray-500" />}
            </h4>
            <p className="text-sm text-gray-600">
              {hasPremiumAccess() ? "Advanced and premium modes with deep analysis" : "Requires premium subscription"}
            </p>
            <div className="space-y-2">
              <Button 
                onClick={() => handleRunAiScreener("advanced", "medium")}
                disabled={!hasPremiumAccess() || isRunningScreener}
                variant={hasPremiumAccess() ? "outline" : "secondary"}
                className="w-full"
              >
                <TrendingUp className="mr-2 h-4 w-4" />
                Advanced Analysis
              </Button>
              <Button 
                onClick={() => handleRunAiScreener("premium", "deep")}
                disabled={!hasPremiumAccess() || isRunningScreener}
                variant={hasPremiumAccess() ? "outline" : "secondary"}
                className="w-full"
              >
                <TrendingDown className="mr-2 h-4 w-4" />
                Premium Analysis
              </Button>
            </div>
            {!hasPremiumAccess() && (
              <Button 
                variant="outline" 
                onClick={() => router.push("/pricing")}
                className="w-full mt-2"
              >
                Upgrade Plan
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <PageHeader 
        title="AI Screener"
        subtitle="Analyze market news, announcements, and search for specific information"
      />

      {/* Status Bar */}
      <StatusBar />

      {/* Date Selector */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CalendarIcon className="h-5 w-5 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Date:</span>
              <span className="text-sm text-gray-600">{format(date, "MMM dd, yyyy")}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDate(new Date())}
              >
                Today
              </Button>
              <DatePicker
                selected={date}
                onSelect={(newDate: Date | undefined) => newDate && setDate(newDate)}
                placeholder="Select date"
              />
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="news">Latest News Analysis</TabsTrigger>
          <TabsTrigger value="announcements">Announcements (NSE/BSE)</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="run">Run Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="news">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <NewsTable
              title="Top 10 Strong Positive"
              sentimentType="positive"
              loading={newsLoading || planCheckLoading}
              data={positiveNews}
              onRefresh={fetchNewsData}
            />
            <NewsTable
              title="Top 10 Strong Negative"
              sentimentType="negative"
              loading={newsLoading || planCheckLoading}
              data={negativeNews}
              onRefresh={fetchNewsData}
            />
          </div>
        </TabsContent>

        <TabsContent value="announcements">
          <AnnouncementsTable
            loading={announcementsLoading || planCheckLoading}
            data={filteredAnnouncements}
            onRefresh={fetchAnnouncementsData}
          />
        </TabsContent>

        <TabsContent value="search">
          <SearchTable
            loading={searchLoading || planCheckLoading}
            data={searchResults}
            query={searchQuery}
            onSearch={fetchSearchData}
            onRefresh={() => fetchSearchData(debouncedSearchQuery)}
          />
        </TabsContent>

        <TabsContent value="history">
          <HistoryTable />
        </TabsContent>

        <TabsContent value="run">
          <RunScreenerCard />
        </TabsContent>
      </Tabs>

      {/* Run Screener Modal */}
      <RunScreenerModal
        isOpen={showRunModal}
        onClose={() => setShowRunModal(false)}
        onRun={handleRunAiScreener}
        isRunning={isRunningScreener}
      />
    </div>
  );
}
