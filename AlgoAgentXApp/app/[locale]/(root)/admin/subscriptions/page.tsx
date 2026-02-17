"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CreditCard, Search, RefreshCw, Eye, Filter } from "lucide-react"
import { adminApi, Subscription } from "@/lib/api/admin"
import { AdminTable } from "@/components/admin/admin-table"
import { toast } from "sonner"
import { parseApiError, formatErrorMessage } from "@/lib/api/error"

export default function AdminSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [skip, setSkip] = useState(0)
  const [limit] = useState(20)
  const [total, setTotal] = useState(0)

  const fetchSubscriptions = async (newSkip?: number) => {
    try {
      setLoading(true)
      setError(null)
      const skipValue = newSkip !== undefined ? newSkip : skip
      const result = await adminApi.getSubscriptions(skipValue, limit, statusFilter || undefined)
      setSubscriptions(result.items)
      setTotal(result.total)
      if (newSkip !== undefined) setSkip(newSkip)
    } catch (err) {
      console.error("Error fetching subscriptions:", err)
      const errorInfo = parseApiError(err);
      const errorMessage = formatErrorMessage(errorInfo);
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (searchValue: string) => {
    setSearch(searchValue)
    setSkip(0)
    setTimeout(() => {
      fetchSubscriptions(0)
    }, 300)
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setSkip(0)
    fetchSubscriptions(0)
  }

  const handleRefresh = () => {
    fetchSubscriptions()
  }

  useEffect(() => {
    fetchSubscriptions()
  }, [])

  const columns = [
    {
      key: 'user_id' as const,
      label: 'User ID',
      render: (userId: string) => (
        <div className="font-mono text-sm">{userId.substring(0, 8)}...</div>
      )
    },
    {
      key: 'plan_code' as const,
      label: 'Plan',
      render: (planCode: string) => (
        <Badge variant="default">{planCode}</Badge>
      )
    },
    {
      key: 'billing_period' as const,
      label: 'Period',
      render: (period: string) => (
        <Badge variant="outline">{period}</Badge>
      )
    },
    {
      key: 'price_inr' as const,
      label: 'Price',
      render: (price: number) => (
        <div className="font-medium">₹{price.toLocaleString()}</div>
      )
    },
    {
      key: 'included_credits' as const,
      label: 'Credits',
      render: (credits: number) => (
        <div className="text-sm">{credits}</div>
      )
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => (
        <Badge 
          variant={status === 'ACTIVE' ? "default" : status === 'PENDING' ? "secondary" : "destructive"}
        >
          {status}
        </Badge>
      )
    },
    {
      key: 'start_at' as const,
      label: 'Start Date',
      render: (date: string) => (
        <div className="text-sm text-gray-500">
          {new Date(date).toLocaleDateString()}
        </div>
      )
    },
    {
      key: 'end_at' as const,
      label: 'End Date',
      render: (date: string) => (
        <div className="text-sm text-gray-500">
          {new Date(date).toLocaleDateString()}
        </div>
      )
    }
  ]

  const actions = [
    {
      label: 'View Details',
      onClick: (subscription: Subscription) => {
        toast.info(`Subscription ID: ${subscription.id}`)
      },
      variant: "outline" as const,
      icon: <Eye className="h-4 w-4" />
    }
  ]

  const statusOptions = [
    { value: "", label: "All Statuses" },
    { value: "ACTIVE", label: "Active" },
    { value: "PENDING", label: "Pending" },
    { value: "EXPIRED", label: "Expired" },
    { value: "CANCELLED", label: "Cancelled" }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Subscription Management</h1>
          <p className="text-muted-foreground">View and manage user subscriptions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
          <CardDescription>Filter subscriptions by status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search by user ID..."
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-64"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <select
                value={statusFilter}
                onChange={(e) => handleStatusFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <AdminTable<Subscription>
        title="Subscriptions"
        columns={columns}
        data={subscriptions}
        loading={loading}
        error={error}
        onRefresh={handleRefresh}
        onSearch={handleSearch}
        searchPlaceholder="Search subscriptions..."
        emptyMessage="No subscriptions found"
        actions={actions}
      />

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {skip + 1} - {Math.min(skip + limit, total)} of {total} subscriptions
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => fetchSubscriptions(Math.max(0, skip - limit))}
              disabled={skip === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => fetchSubscriptions(skip + limit)}
              disabled={skip + limit >= total}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}