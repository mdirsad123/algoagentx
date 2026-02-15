"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, AlertCircle } from "lucide-react";

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
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "disconnected":
        return <XCircle className="h-5 w-5 text-red-500" />;
      case "error":
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return <Badge variant="default">Connected</Badge>;
      case "disconnected":
        return <Badge variant="destructive">Disconnected</Badge>;
      case "error":
        return <Badge variant="secondary">Error</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Trading Brokers</h1>
        <p className="text-gray-600 mt-2">
          View your connected trading brokers
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {brokers.map((broker, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg font-semibold">
                {broker.name}
              </CardTitle>
              {getStatusIcon(broker.status)}
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Status</span>
                {getStatusBadge(broker.status)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">API Key</span>
                <span className="text-sm font-mono">{broker.apiKey}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Last Sync</span>
                <span className="text-sm">{broker.lastSync}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Broker Integration Guide</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium mb-2">Supported Brokers</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Zerodha (Kite Connect)</li>
                <li>• Upstox</li>
                <li>• Angel One</li>
                <li>• FYERS</li>
                <li>• Alice Blue</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-2">API Requirements</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Valid API Key</li>
                <li>• API Secret</li>
                <li>• Access Token</li>
                <li>• WebSocket Connection</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}