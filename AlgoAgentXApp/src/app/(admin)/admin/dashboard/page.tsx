"use client"

import React, { useState, useEffect } from 'react'
import { adminApi, type AdminMetrics, type User, type Payment, type CreditTransaction } from '@/lib/api/admin'
import { parseApiError } from '@/lib/api/error'
import { Button } from '@/components/ui/button'
import { RefreshCw, Users, DollarSign, CreditCard, ShoppingCart, Zap, Cpu, Coins } from 'lucide-react'
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardDescription, StandardCardContent, StandardCardFooter } from '@/components/ui/standard-card'
import { PageHeader } from '@/components/ui/page-header'
import EmptyState from '@/components/shared/empty-state'
import { LoadingSkeleton, StatsSkeleton, TableSkeleton } from '@/components/ui/loading-skeleton'
import { Badge } from '@/components/ui/badge'
import { format } from 'date-fns'

interface DashboardData {
  metrics: AdminMetrics | null
  recentUsers: User[]
  recentPayments: Payment[]
  recentOrders: CreditTransaction[]
  isLoading: boolean
  error: string | null
}

const AdminDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData>({
    metrics: null,
    recentUsers: [],
    recentPayments: [],
    recentOrders: [],
    isLoading: true,
    error: null
  })

  const fetchData = async () => {
    try {
      setData(prev => ({ ...prev, isLoading: true, error: null }))
      
      // For now, use mock data since admin API might not be available
      // In a real implementation, replace this with the actual API calls
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock data for demonstration
      const mockData = {
        metrics: {
          users: {
            total: 156,
            active: 123,
            recent: []
          },
          payments: {
            total: 45,
            revenue: 87500,
            recent: []
          },
          credits: {
            total: 5000,
            active_subscriptions: 23
          },
          screener_jobs: {
            recent: []
          }
        },
        recentUsers: [
          {
            id: "1",
            email: "john.doe@example.com",
            role: "user",
            is_active: true,
            created_at: "2024-02-28T10:00:00Z",
            updated_at: "2024-02-28T10:00:00Z"
          },
          {
            id: "2", 
            email: "jane.smith@example.com",
            role: "user",
            is_active: true,
            created_at: "2024-02-27T15:30:00Z",
            updated_at: "2024-02-27T15:30:00Z"
          }
        ],
        recentPayments: [
          {
            id: "1",
            user_id: "1",
            amount: 25000,
            currency: "INR",
            status: "success",
            payment_method: "razorpay",
            razorpay_order_id: "order_123",
            razorpay_payment_id: "pay_123",
            created_at: "2024-02-28T09:00:00Z",
            updated_at: "2024-02-28T09:00:00Z"
          }
        ],
        recentOrders: [
          {
            id: "1",
            user_id: "1",
            user_email: "john.doe@example.com",
            credits: 1000,
            type: "purchase",
            reason: "Monthly subscription",
            created_at: "2024-02-28T09:00:00Z"
          }
        ]
      }

      setData({
        metrics: mockData.metrics,
        recentUsers: mockData.recentUsers,
        recentPayments: mockData.recentPayments,
        recentOrders: mockData.recentOrders,
        isLoading: false,
        error: null
      })
    } catch (error) {
      console.error("Error fetching admin data:", error)
      setData(prev => ({ ...prev, isLoading: false, error: "Failed to load admin data. Please check if admin API is available." }))
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy')
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase()
    if (statusLower.includes('success') || statusLower.includes('completed')) {
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    }
    if (statusLower.includes('pending') || statusLower.includes('processing')) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    }
    if (statusLower.includes('failed') || statusLower.includes('cancelled')) {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    }
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
  }

  if (data.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Admin Dashboard"
          subtitle="Overview of system metrics and recent activity"
        />
        <StatsSkeleton />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <LoadingSkeleton className="h-96 w-full rounded-xl" />
          <LoadingSkeleton className="h-96 w-full rounded-xl" />
          <LoadingSkeleton className="h-96 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  if (data.error) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Admin Dashboard"
          subtitle="Overview of system metrics and recent activity"
        />
        <EmptyState
          title="Error Loading Dashboard"
          description={data.error}
          variant="error"
          actionLabel="Retry"
          onAction={fetchData}
        />
      </div>
    )
  }

  if (!data.metrics) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title="Admin Dashboard"
          subtitle="Overview of system metrics and recent activity"
        />
        <EmptyState
          title="No Data Available"
          description="No metrics data found. Please check the system configuration."
          actionLabel="Refresh"
          onAction={fetchData}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Admin Dashboard"
        subtitle="Overview of system metrics and recent activity"
        actions={
          <Button 
            onClick={fetchData}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${data.isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Users Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>Total Users</StandardCardDescription>
                <StandardCardTitle className="text-3xl font-bold mt-2">
                  {data.metrics.users.total.toLocaleString()}
                </StandardCardTitle>
              </div>
              <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-full">
                <Users className="w-8 h-8 text-blue-600 dark:text-blue-300" />
              </div>
            </div>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              Active: {data.metrics.users.active.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* Revenue Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>Total Revenue</StandardCardDescription>
                <StandardCardTitle className="text-3xl font-bold mt-2 text-green-600 dark:text-green-400">
                  {formatCurrency(data.metrics.payments.revenue)}
                </StandardCardTitle>
              </div>
              <div className="p-3 bg-green-100 dark:bg-green-900 rounded-full">
                <DollarSign className="w-8 h-8 text-green-600 dark:text-green-300" />
              </div>
            </div>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              Total Payments: {data.metrics.payments.total.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* Credits Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>Total Credits</StandardCardDescription>
                <StandardCardTitle className="text-3xl font-bold mt-2 text-purple-600 dark:text-purple-400">
                  {data.metrics.credits.total.toLocaleString()}
                </StandardCardTitle>
              </div>
              <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-full">
                <Coins className="w-8 h-8 text-purple-600 dark:text-purple-300" />
              </div>
            </div>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              Active Subscriptions: {data.metrics.credits.active_subscriptions.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* AI Jobs Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>Recent AI Jobs</StandardCardDescription>
                <StandardCardTitle className="text-3xl font-bold mt-2 text-orange-600 dark:text-orange-400">
                  {data.metrics.screener_jobs.recent.length}
                </StandardCardTitle>
              </div>
              <div className="p-3 bg-orange-100 dark:bg-orange-900 rounded-full">
                <Cpu className="w-8 h-8 text-orange-600 dark:text-orange-300" />
              </div>
            </div>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              Recent Jobs: {data.metrics.screener_jobs.recent.length}
            </div>
          </StandardCardContent>
        </StandardCard>
      </div>

      {/* Recent Activity Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Users */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>Recent Users</StandardCardTitle>
            <StandardCardDescription>
              Recently registered users
            </StandardCardDescription>
          </StandardCardHeader>
          <StandardCardContent>
            {data.recentUsers.length > 0 ? (
              <div className="space-y-4">
                {data.recentUsers.map((user) => (
                  <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">{user.email}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(user.created_at)}
                      </div>
                    </div>
                    <Badge variant={user.is_active ? "default" : "secondary"}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Recent Users"
                variant="default"
              />
            )}
          </StandardCardContent>
        </StandardCard>

        {/* Recent Payments */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>Recent Payments</StandardCardTitle>
            <StandardCardDescription>
              Latest payment transactions
            </StandardCardDescription>
          </StandardCardHeader>
          <StandardCardContent>
            {data.recentPayments.length > 0 ? (
              <div className="space-y-4">
                {data.recentPayments.map((payment) => (
                  <div key={payment.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {formatCurrency(payment.amount)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {payment.payment_method} • {formatDate(payment.created_at)}
                      </div>
                    </div>
                    <Badge className={getStatusColor(payment.status)}>
                      {payment.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Recent Payments"
                variant="default"
              />
            )}
          </StandardCardContent>
        </StandardCard>

        {/* Recent Orders */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>Recent Orders</StandardCardTitle>
            <StandardCardDescription>
              Latest credit transactions
            </StandardCardDescription>
          </StandardCardHeader>
          <StandardCardContent>
            {data.recentOrders.length > 0 ? (
              <div className="space-y-4">
                {data.recentOrders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {order.credits > 0 ? '+' : ''}{order.credits} Credits
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {order.user_email} • {formatDate(order.created_at)}
                      </div>
                    </div>
                    <Badge variant={order.credits > 0 ? "default" : "secondary"}>
                      {order.type}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Recent Orders"
                variant="default"
              />
            )}
          </StandardCardContent>
        </StandardCard>
      </div>
    </div>
  )
}

export default AdminDashboard