import * as React from "react"
import { useState, useEffect } from "react"
import { toast } from "@/components/ui/use-toast"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Loader2, RefreshCw, Eye, Clock, Calendar, User } from "lucide-react"

interface StrategyRequest {
  id: string
  title: string
  strategy_type: string | null
  market: string | null
  timeframe: string | null
  status: string
  user_id: string
  created_at: string
  updated_at: string
  admin_notes: string | null
}

type StrategyStatus = "UNDER_DEVELOPMENT" | "NEEDS_CLARIFICATION" | "REJECTED" | "DEPLOYED"

const statusConfig = {
  UNDER_DEVELOPMENT: {
    label: "Under Development",
    color: "bg-blue-100 text-blue-800",
    icon: Clock,
  },
  NEEDS_CLARIFICATION: {
    label: "Needs Clarification",
    color: "bg-yellow-100 text-yellow-800",
    icon: Eye,
  },
  REJECTED: {
    label: "Rejected",
    color: "bg-red-100 text-red-800",
    icon: Calendar,
  },
  DEPLOYED: {
    label: "Deployed",
    color: "bg-green-100 text-green-800",
    icon: User,
  },
}

export function MyStrategyRequests() {
  const [requests, setRequests] = useState<StrategyRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchRequests = async () => {
    try {
      setLoading(true)
      const response = await fetch("/api/v1/strategy-requests/me")
      
      if (!response.ok) {
        throw new Error("Failed to fetch strategy requests")
      }

      const data = await response.json()
      setRequests(data)
    } catch (error) {
      console.error("Error fetching strategy requests:", error)
      toast({
        variant: "destructive",
        title: "Failed to Load Requests",
        description: "Unable to fetch your strategy requests. Please try again.",
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchRequests()
  }, [])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchRequests()
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadge = (status: StrategyStatus) => {
    const config = statusConfig[status]
    const IconComponent = config.icon
    
    return (
      <Badge className={`inline-flex items-center gap-1 ${config.color}`}>
        <IconComponent className="h-3 w-3" />
        {config.label}
      </Badge>
    )
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>My Strategy Requests</CardTitle>
          <CardDescription>Loading your strategy requests...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0">
        <div>
          <CardTitle>My Strategy Requests</CardTitle>
          <CardDescription>
            Track the status of your custom strategy requests
          </CardDescription>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="w-full sm:w-auto"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </CardHeader>
      
      <CardContent>
        {requests.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>You haven't submitted any strategy requests yet.</p>
            <p className="text-sm mt-2">Submit a request to get started with custom strategy development.</p>
          </div>
        ) : (
          <div className="max-h-[400px] overflow-y-auto pr-4">
            <div className="space-y-6">
              {requests.map((request, index) => (
                <div key={request.id} className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {request.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        {request.strategy_type && (
                          <Badge variant="secondary" className="text-xs">
                            {request.strategy_type}
                          </Badge>
                        )}
                        {request.market && (
                          <Badge variant="secondary" className="text-xs">
                            {request.market}
                          </Badge>
                        )}
                        {request.timeframe && (
                          <Badge variant="secondary" className="text-xs">
                            {request.timeframe}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(request.status as StrategyStatus)}
                      <span className="text-xs text-gray-500">
                        Updated: {formatDate(request.updated_at)}
                      </span>
                    </div>
                  </div>

                  {request.admin_notes && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-2">Admin Notes:</h4>
                      <p className="text-sm text-gray-700">{request.admin_notes}</p>
                    </div>
                  )}

                  <div className="text-xs text-gray-500">
                    Requested: {formatDate(request.created_at)}
                  </div>

                  <Separator />

                  {index < requests.length - 1 && <Separator className="my-6" />}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}