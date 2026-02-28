"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/enhanced-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTranslation } from "@/hooks/use-translations";
import { useNotifications } from "@/contexts/notification-context";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { StrategyRequestForm } from "@/components/strategies/StrategyRequestForm";
import { MyStrategyRequests } from "@/components/strategies/MyStrategyRequests";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/shared/EmptyState";
import { Plus } from "lucide-react";
import AppShell from "@/components/layout/AppShell";

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

export default function StrategiesPage() {
  const [activeTab, setActiveTab] = useState("templates");
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [myStrategies, setMyStrategies] = useState<StrategyMy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { t } = useTranslation();
  const { notifications, unreadCount } = useNotifications();
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
        const data = await response.json();
        setTemplates(data);
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
        const data = await response.json();
        setMyStrategies(data);
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
      toast.error("Please log in to backtest strategies");
      return;
    }
    router.push(`/backtest?strategyId=${strategyId}`);
  };

  const renderStrategyCard = (strategy: StrategyTemplate | StrategyMy) => (
    <Card key={strategy.id} variant="elevated" className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{strategy.name}</CardTitle>
          <Badge variant={strategy.status === 'active' ? 'default' : 'secondary'}>
            {strategy.status}
          </Badge>
        </div>
        <p className="text-sm text-gray-600">{strategy.description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Win Rate</span>
              <span className="text-sm font-medium text-green-600">
                {strategy.winRate ? `${strategy.winRate}%` : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Total Trades</span>
              <span className="text-sm font-medium text-gray-900">
                {strategy.totalTrades || "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Profit Factor</span>
              <span className="text-sm font-medium text-gray-900">
                {strategy.profitFactor || "N/A"}
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Sharpe Ratio</span>
              <span className="text-sm font-medium text-gray-900">
                {strategy.sharpeRatio || "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Max Drawdown</span>
              <span className="text-sm font-medium text-red-600">
                {strategy.maxDrawdown ? `${strategy.maxDrawdown}%` : "N/A"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Last Updated</span>
              <span className="text-sm font-medium text-gray-900">
                {new Date(strategy.lastUpdated).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-2">
          <Button
            onClick={() => handleBacktest(strategy.id)}
            className="w-full"
          >
            Backtest
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderEmptyState = (tab: string) => (
    <EmptyState
      title={tab === "templates" ? "No Strategy Templates" : 
             tab === "my" ? "No Strategies Found" : 
             "No Strategy Requests"}
      description={tab === "templates" ? "Browse our strategy templates to get started" : 
                  tab === "my" ? "You don't have any strategies yet" : 
                  "No strategy requests found"}
      action={tab === "request" && (
        <Button onClick={() => router.push("/strategies/request")} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Request a Strategy
        </Button>
      )}
    />
  );

  return (
    <AppShell pageTitle="Trading Strategies">
      <div className="space-y-6">
      <PageHeader 
        title="Trading Strategies"
        subtitle="Browse templates, manage your strategies, or request custom strategies"
        actions={
          <Button onClick={() => router.push("/strategies/request")} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Request Strategy
          </Button>
        }
      />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="request">Request Strategy</TabsTrigger>
          <TabsTrigger value="my">My Strategies</TabsTrigger>
        </TabsList>

        <TabsContent value="templates">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(4)].map((_, index) => (
                <Card key={index} variant="elevated" className="animate-pulse">
                  <CardHeader>
                    <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-full"></div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {[...Array(6)].map((_, i) => (
                        <div key={i} className="h-4 bg-gray-200 rounded"></div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
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
        </TabsContent>

        <TabsContent value="request">
          <div className="space-y-6">
            <StrategyRequestForm onSuccess={() => setActiveTab("request")} />
            <MyStrategyRequests />
          </div>
        </TabsContent>

        <TabsContent value="my">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[...Array(2)].map((_, index) => (
                <Card key={index} variant="elevated" className="animate-pulse">
                  <CardHeader>
                    <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-full"></div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {[...Array(6)].map((_, i) => (
                        <div key={i} className="h-4 bg-gray-200 rounded"></div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : myStrategies.length === 0 ? (
            renderEmptyState("my")
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {myStrategies.map(renderStrategyCard)}
            </div>
          )}
        </TabsContent>
      </Tabs>
      </div>
    </AppShell>
  );
}
