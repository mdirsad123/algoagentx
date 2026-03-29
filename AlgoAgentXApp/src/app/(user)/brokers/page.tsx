"use client";

import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, AlertCircle, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageShell } from "@/components/ui/PageShell";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { GlassCard } from "@/components/ui/GlassCard";

export default function BrokersPage() {
  const brokers = [
    {
      name: "Zerodha",
      status: "connected",
      lastSync: "2024-01-07 10:30",
      apiKey: "****1234",
    },
    {
      name: "Upstox",
      status: "connected",
      lastSync: "2024-01-07 09:45",
      apiKey: "****5678",
    },
    {
      name: "Angel One",
      status: "disconnected",
      lastSync: "2024-01-06 15:20",
      apiKey: "****9012",
    },
    {
      name: "FYERS",
      status: "error",
      lastSync: "2024-01-07 08:10",
      apiKey: "****3456",
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "connected":
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case "disconnected":
        return <XCircle className="h-5 w-5 text-red-400" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-yellow-400" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return <Badge variant="default" className="bg-green-500/20 border-green-500/30">Connected</Badge>;
      case "disconnected":
        return <Badge variant="destructive" className="bg-red-500/20 border-red-500/30">Disconnected</Badge>;
      case "error":
        return <Badge variant="secondary" className="bg-yellow-500/20 border-yellow-500/30">Error</Badge>;
      default:
        return null;
    }
  };

  return (
    <PageShell>
      <PageHeader 
        title="Trading Brokers"
        subtitle="View your connected trading brokers"
        actions={
          <Button className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0">
            <Plus className="h-4 w-4" />
            Connect Broker
          </Button>
        }
      />

      <div className="space-y-6">
        {brokers.length === 0 ? (
          <EmptyState
            title="No Brokers Connected"
            description="Connect your trading brokers to start using AlgoAgentX"
            action={
              <Button className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0">
                <Plus className="h-4 w-4" />
                Connect Broker
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {brokers.map((broker, index) => (
              <GlassCard key={index} className="hover:scale-105 transition-transform duration-300">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">
                      {broker.name}
                    </h3>
                    {getStatusIcon(broker.status)}
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-purple-200 text-sm">Status</span>
                      {getStatusBadge(broker.status)}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-purple-200 text-sm">API Key</span>
                      <span className="text-sm font-mono text-white">{broker.apiKey}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-purple-200 text-sm">Last Sync</span>
                      <span className="text-sm text-white">{broker.lastSync}</span>
                    </div>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}

        <GlassCard>
          <div className="p-6">
            <h3 className="text-xl font-bold bg-gradient-to-r from-white via-purple-200 to-purple-300 bg-clip-text text-transparent mb-4">
              Broker Integration Guide
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-2 text-purple-200">Supported Brokers</h4>
                <ul className="text-sm text-purple-300 space-y-1">
                  <li>• Zerodha (Kite Connect)</li>
                  <li>• Upstox</li>
                  <li>• Angel One</li>
                  <li>• FYERS</li>
                  <li>• Alice Blue</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2 text-purple-200">API Requirements</h4>
                <ul className="text-sm text-purple-300 space-y-1">
                  <li>• Valid API Key</li>
                  <li>• API Secret</li>
                  <li>• Access Token</li>
                  <li>• WebSocket Connection</li>
                </ul>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>
    </PageShell>
  );
}