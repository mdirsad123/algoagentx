"use client";

import { useState, useEffect, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { RequestStrategyModal } from "@/components/strategies/RequestStrategyModal";

interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  status: string;
  winRate: number | null;
  sharpeRatio: number | null;
  totalTrades: number | null;
  maxDrawdown: number | null;
  profitFactor: number | null;
  lastUpdated: string;
}

interface StrategyMy {
  id: string;
  name: string;
  description: string;
  status: string;
  winRate: number | null;
  sharpeRatio: number | null;
  totalTrades: number | null;
  maxDrawdown: number | null;
  profitFactor: number | null;
  lastUpdated: string;
}

const unwrapApiData = (payload: any) => payload?.success ? payload.data : payload;

export default function StrategiesPage() {
  const [activeTab, setActiveTab] = useState("templates");
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [myStrategies, setMyStrategies] = useState<StrategyMy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const router = useRouter();
  
  // Get user from localStorage or auth context
  const user = useMemo(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          // Decode JWT to get user info (basic implementation)
          const payload = JSON.parse(atob(token.split('.')[1]));
          return {
            id: payload.sub,
            token: token,
            role: payload.role
          };
        } catch (e) {
          return null;
        }
      }
    }
    return null;
  }, []);

  // Fetch templates
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setLoading(true);
        const response = await fetch("/api/v1/strategies/templates");
        if (!response.ok) {
          throw new Error("Failed to fetch templates");
        }
        const raw = await response.json();
        const data = unwrapApiData(raw);
        setTemplates(unwrapApiData(data));
      } catch (err) {
        console.error("Error fetching templates:", err);
        setError("Failed to load strategy templates");
      } finally {
        setLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  // Fetch user strategies
  useEffect(() => {
    const fetchMyStrategies = async () => {
      if (!user) return;
      
      try {
        setLoading(true);
        const response = await fetch("/api/v1/strategies/my", {
          headers: {
            Authorization: `Bearer ${user.token}`,
          },
        });
        if (!response.ok) {
          throw new Error("Failed to fetch user strategies");
        }
        const raw = await response.json();
        const data = unwrapApiData(raw);
        setMyStrategies(unwrapApiData(data));
      } catch (err) {
        console.error("Error fetching user strategies:", err);
        // Don't show error for user strategies as they might not have any
      } finally {
        setLoading(false);
      }
    };

    fetchMyStrategies();
  }, [user]);

  const handleBacktest = (strategyId: string) => {
    if (!user) {
      // Use a simple alert for now since we don't have toast configured
      alert("Please log in to backtest strategies");
      return;
    }
    router.push(`/backtest?strategyId=${strategyId}`);
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleModalSuccess = () => {
    // Optionally refresh data or show additional feedback
    console.log("Strategy request submitted successfully");
  };

  const renderStrategyCard = (strategy: StrategyTemplate | StrategyMy) => (
    <GlassCard key={strategy.id} className="h-full hover:scale-105 transition-transform duration-300">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            {strategy.name}
          </h3>
          <Badge variant={strategy.status === 'active' ? 'default' : 'secondary'} 
                 className={strategy.status === 'active' 
                   ? "bg-green-500/20 border-green-500/30" 
                   : "bg-yellow-500/20 border-yellow-500/30"}>
            {strategy.status}
          </Badge>
        </div>
        <p className="text-sm text-purple-200 mb-4">{strategy.description}</p>
        
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Win Rate</span>
              <span className="text-sm font-medium text-green-400">
                {strategy.winRate ? `${strategy.winRate}%` : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Total Trades</span>
              <span className="text-sm font-medium text-white">
                {strategy.totalTrades || "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Profit Factor</span>
              <span className="text-sm font-medium text-white">
                {strategy.profitFactor || "N/A"}
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Sharpe Ratio</span>
              <span className="text-sm font-medium text-white">
                {strategy.sharpeRatio || "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Max Drawdown</span>
              <span className="text-sm font-medium text-red-400">
                {strategy.maxDrawdown ? `${strategy.maxDrawdown}%` : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-300">Last Updated</span>
              <span className="text-sm font-medium text-white">
                {new Date(strategy.lastUpdated).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            onClick={() => handleBacktest(strategy.id)}
            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0"
          >
            Backtest
          </Button>
        </div>
      </div>
    </GlassCard>
  );

  const renderEmptyState = (tab: string) => (
    <EmptyState
      title={tab === "templates" ? "No Strategy Templates" : 
             tab === "my" ? "No Strategies Found" : 
             "No Strategy Requests"}
      description={tab === "templates" ? "Browse our strategy templates to get started" : 
                   tab === "my" ? "You don't have any strategies yet" : 
                   "No strategy requests found"}
      action={tab === "request" ? (
        <Button onClick={handleOpenModal} className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0">
          <Plus className="h-4 w-4" />
          Request a Strategy
        </Button>
      ) : undefined}
    />
  );

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Trading Strategies"
        subtitle="Browse templates, manage your strategies, or request custom strategies"
        actions={
          <Button onClick={handleOpenModal} className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0">
            <Plus className="h-4 w-4" />
            Request Strategy
          </Button>
        }
      />

      <div className="space-y-4">
        {/* Custom Tab Navigation */}
        <div className="bg-card/30 border border-border/50 rounded-lg p-2">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab("templates")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                activeTab === "templates"
                  ? "bg-primary/20 text-primary border border-primary/30"
                  : "text-purple-200 hover:text-white hover:bg-primary/10"
              }`}
            >
              Templates
            </button>
            <button
              onClick={() => setActiveTab("request")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                activeTab === "request"
                  ? "bg-primary/20 text-primary border border-primary/30"
                  : "text-purple-200 hover:text-white hover:bg-primary/10"
              }`}
            >
              Request Strategy
            </button>
            <button
              onClick={() => setActiveTab("my")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                activeTab === "my"
                  ? "bg-primary/20 text-primary border border-primary/30"
                  : "text-purple-200 hover:text-white hover:bg-primary/10"
              }`}
            >
              My Strategies
            </button>
          </div>
        </div>

        {/* Templates Tab Content */}
        {activeTab === "templates" && (
          <div>
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[...Array(4)].map((_, index) => (
                  <GlassCard key={index} className="animate-pulse">
                    <div className="p-6">
                      <div className="h-6 bg-white/20 rounded w-3/4 mb-2"></div>
                      <div className="h-4 bg-white/20 rounded w-full mb-4"></div>
                      <div className="space-y-2">
                        {[...Array(6)].map((_, i) => (
                          <div key={i} className="h-4 bg-white/20 rounded"></div>
                        ))}
                      </div>
                    </div>
                  </GlassCard>
                ))}
              </div>
            ) : error ? (
              <div className="text-red-500 text-center py-8">{error}</div>
            ) : templates.length === 0 ? (
              renderEmptyState("templates")
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {templates.map(renderStrategyCard)}
              </div>
            )}
          </div>
        )}

        {/* Request Strategy Tab Content */}
        {activeTab === "request" && (
          <GlassCard>
            <div className="p-6">
              <h3 className="text-xl font-bold bg-gradient-to-r from-white via-purple-200 to-purple-300 bg-clip-text text-transparent mb-4">
                Request Custom Strategy
              </h3>
              <p className="text-purple-200 mb-6">
                Looking for a specific trading strategy? Our team of experts can help you create custom strategies tailored to your trading style and goals.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-2 text-purple-200">What We Need</h4>
                  <ul className="text-sm text-purple-300 space-y-1">
                    <li>• Trading style preference</li>
                    <li>• Risk tolerance level</li>
                    <li>• Timeframe requirements</li>
                    <li>• Market preferences</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2 text-purple-200">Our Process</h4>
                  <ul className="text-sm text-purple-300 space-y-1">
                    <li>• Strategy design</li>
                    <li>• Backtesting & optimization</li>
                    <li>• Risk management</li>
                    <li>• Implementation support</li>
                  </ul>
                </div>
              </div>
              <div className="mt-6 flex justify-center">
                <Button onClick={handleOpenModal} className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0">
                  Request Strategy
                </Button>
              </div>
            </div>
          </GlassCard>
        )}

        {/* My Strategies Tab Content */}
        {activeTab === "my" && (
          <div>
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[...Array(2)].map((_, index) => (
                  <GlassCard key={index} className="animate-pulse">
                    <div className="p-6">
                      <div className="h-6 bg-white/20 rounded w-3/4 mb-2"></div>
                      <div className="h-4 bg-white/20 rounded w-full mb-4"></div>
                      <div className="space-y-2">
                        {[...Array(6)].map((_, i) => (
                          <div key={i} className="h-4 bg-white/20 rounded"></div>
                        ))}
                      </div>
                    </div>
                  </GlassCard>
                ))}
              </div>
            ) : myStrategies.length === 0 ? (
              renderEmptyState("my")
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {myStrategies.map(renderStrategyCard)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Request Strategy Modal */}
      <RequestStrategyModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSuccess={handleModalSuccess}
      />
    </div>
  );
}
