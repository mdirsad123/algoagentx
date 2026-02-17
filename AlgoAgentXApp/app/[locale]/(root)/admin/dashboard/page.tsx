import React, { useState, useEffect } from 'react'
import { useTranslation } from '@/hooks/use-translations'
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
  const { t } = useTranslation()
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
      
      // Fetch all data in parallel
      const [metricsResponse, usersResponse, paymentsResponse, ordersResponse] = await Promise.all([
        adminApi.getMetrics(),
        adminApi.getUsers(0, 5),
        adminApi.getPayments(0, 5),
        adminApi.getCredits(0, 5)
      ])

      setData({
        metrics: metricsResponse,
        recentUsers: usersResponse.items,
        recentPayments: paymentsResponse.items,
        recentOrders: ordersResponse.items,
        isLoading: false,
        error: null
      })
    } catch (error) {
      const parsedError = parseApiError(error)
      const errorMessage = parsedError.message || t('admin.dashboard.error.fetchFailed')
      
      setData(prev => ({ ...prev, isLoading: false, error: errorMessage }))
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
          title={t('admin.dashboard.title')}
          subtitle={t('admin.dashboard.subtitle')}
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
          title={t('admin.dashboard.title')}
          subtitle={t('admin.dashboard.subtitle')}
        />
        <EmptyState
          title={t('admin.dashboard.error.title')}
          description={data.error}
          variant="error"
          actionLabel={t('admin.dashboard.error.retry')}
          onAction={fetchData}
        />
      </div>
    )
  }

  if (!data.metrics) {
    return (
      <div className="space-y-6">
        <PageHeader 
          title={t('admin.dashboard.title')}
          subtitle={t('admin.dashboard.subtitle')}
        />
        <EmptyState
          title={t('admin.dashboard.empty.title')}
          description={t('admin.dashboard.empty.description')}
          actionLabel={t('admin.dashboard.empty.refresh')}
          onAction={fetchData}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title={t('admin.dashboard.title')}
        subtitle={t('admin.dashboard.subtitle')}
        actions={
          <Button 
            onClick={fetchData}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${data.isLoading ? 'animate-spin' : ''}`} />
            {t('admin.dashboard.refresh')}
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
                <StandardCardDescription>{t('admin.dashboard.kpi.users')}</StandardCardDescription>
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
              {t('admin.dashboard.kpi.active')}: {data.metrics.users.active.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* Revenue Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>{t('admin.dashboard.kpi.revenue')}</StandardCardDescription>
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
              {t('admin.dashboard.kpi.totalPayments')}: {data.metrics.payments.total.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* Credits Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>{t('admin.dashboard.kpi.credits')}</StandardCardDescription>
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
              {t('admin.dashboard.kpi.activeSubscriptions')}: {data.metrics.credits.active_subscriptions.toLocaleString()}
            </div>
          </StandardCardContent>
        </StandardCard>

        {/* AI Jobs Card */}
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardDescription>{t('admin.dashboard.kpi.aiJobs')}</StandardCardDescription>
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
              {t('admin.dashboard.kpi.recentJobs')}: {data.metrics.screener_jobs.recent.length}
            </div>
          </StandardCardContent>
        </StandardCard>
      </div>

      {/* Recent Activity Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Users */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>{t('admin.dashboard.recent.users')}</StandardCardTitle>
            <StandardCardDescription>
              {t('admin.dashboard.recent.usersDescription')}
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
                      {user.is_active ? t('admin.dashboard.status.active') : t('admin.dashboard.status.inactive')}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title={t('admin.dashboard.empty.noUsers')}
                variant="default"
              />
            )}
          </StandardCardContent>
        </StandardCard>

        {/* Recent Payments */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>{t('admin.dashboard.recent.payments')}</StandardCardTitle>
            <StandardCardDescription>
              {t('admin.dashboard.recent.paymentsDescription')}
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
                title={t('admin.dashboard.empty.noPayments')}
                variant="default"
              />
            )}
          </StandardCardContent>
        </StandardCard>

        {/* Recent Orders */}
        <StandardCard className="lg:col-span-1">
          <StandardCardHeader>
            <StandardCardTitle>{t('admin.dashboard.recent.orders')}</StandardCardTitle>
            <StandardCardDescription>
              {t('admin.dashboard.recent.ordersDescription')}
            </StandardCardDescription>
          </StandardCardHeader>
          <StandardCardContent>
            {data.recentOrders.length > 0 ? (
              <div className="space-y-4">
                {data.recentOrders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {order.credits > 0 ? '+' : ''}{order.credits} {t('admin.dashboard.credits')}
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
                title={t('admin.dashboard.empty.noOrders')}
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