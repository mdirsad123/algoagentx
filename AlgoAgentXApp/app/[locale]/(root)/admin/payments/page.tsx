"use client"

import React, { useState, useEffect } from "react"
import { useTranslation } from "@/hooks/use-translations"
import { adminApi, Payment } from "@/lib/api/admin"
import { parseApiError } from "@/lib/api/error"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardContent } from "@/components/ui/standard-card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription, DrawerFooter, DrawerClose } from "@/components/ui/drawer"
import { format } from "date-fns"
import { 
  DollarSign, 
  Search, 
  RefreshCw, 
  Eye, 
  Filter, 
  Calendar,
  CreditCard,
  User,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw
} from "lucide-react"
import { LoadingSkeleton, StatsSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton"
import { Pagination } from "@/components/ui/pagination"

interface FilterState {
  status: string
  search: string
  from_date: string
  to_date: string
}

interface PaymentPageState {
  payments: Payment[]
  loading: boolean
  error: string | null
  pagination: {
    total: number
    skip: number
    limit: number
  }
}

export default function AdminPaymentsPage() {
  const { t } = useTranslation()
  const [state, setState] = useState<PaymentPageState>({
    payments: [],
    loading: true,
    error: null,
    pagination: {
      total: 0,
      skip: 0,
      limit: 20
    }
  })
  
  const [filters, setFilters] = useState<FilterState>({
    status: "",
    search: "",
    from_date: "",
    to_date: ""
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [isRefundModalOpen, setIsRefundModalOpen] = useState(false)
  const [paymentToRefund, setPaymentToRefund] = useState<string | null>(null)

  const fetchPayments = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      
      const skip = (currentPage - 1) * state.pagination.limit
      
      const params: any = {
        ...(filters.status && { status: filters.status }),
        ...(filters.search && { search: filters.search }),
        ...(filters.from_date && { from_date: filters.from_date }),
        ...(filters.to_date && { to_date: filters.to_date })
      }

      const response = await adminApi.getPayments(
        skip,
        state.pagination.limit,
        params.status,
        params.search,
        params.from_date,
        params.to_date
      )
      
      setState(prev => ({
        ...prev,
        payments: response.items || [],
        pagination: {
          total: response.total || 0,
          skip: skip,
          limit: state.pagination.limit
        },
        loading: false
      }))
    } catch (error) {
      const parsedError = parseApiError(error)
      const errorMessage = parsedError.message || t('admin.payments.error.fetchFailed')
      
      setState(prev => ({ ...prev, loading: false, error: errorMessage }))
    }
  }

  useEffect(() => {
    fetchPayments()
  }, [currentPage, filters])

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const handleViewDetails = async (paymentId: string) => {
    try {
      const paymentDetails = await adminApi.getPayment(paymentId)
      setSelectedPayment(paymentDetails)
      setIsDetailOpen(true)
    } catch (error) {
      const parsedError = parseApiError(error)
      alert(parsedError.message || t('admin.payments.error.fetchPaymentFailed'))
    }
  }

  const handleRefund = async (paymentId: string) => {
    try {
      // Note: This assumes the backend has a refund endpoint
      // If not available, this will show an error
      await adminApi.refundPayment(paymentId)
      setIsRefundModalOpen(false)
      setPaymentToRefund(null)
      fetchPayments()
    } catch (error) {
      const parsedError = parseApiError(error)
      alert(parsedError.message || t('admin.payments.error.refundFailed'))
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

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency || 'INR'
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy')
    } catch {
      return dateString
    }
  }

  const canRefund = (status: string) => {
    const statusLower = status.toLowerCase()
    return statusLower.includes('success') || statusLower.includes('completed')
  }

  if (state.loading && state.payments.length === 0) {
    return (
      <div className="space-y-6">
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardTitle>{t('admin.payments.title')}</StandardCardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {t('admin.payments.subtitle')}
                </p>
              </div>
              <Button 
                onClick={fetchPayments}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
                {t('admin.payments.refresh')}
              </Button>
            </div>
          </StandardCardHeader>
          <StandardCardContent>
            <StatsSkeleton />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
              <LoadingSkeleton className="h-96 w-full rounded-xl" />
              <LoadingSkeleton className="h-96 w-full rounded-xl" />
              <LoadingSkeleton className="h-96 w-full rounded-xl" />
            </div>
          </StandardCardContent>
        </StandardCard>
      </div>
    )
  }

  if (state.error) {
    return (
      <div className="space-y-6">
        <StandardCard>
          <StandardCardHeader>
            <StandardCardTitle>{t('admin.payments.title')}</StandardCardTitle>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <p className="text-red-600 dark:text-red-400 mb-4">{state.error}</p>
              <Button onClick={fetchPayments} variant="outline">
                {t('admin.payments.retry')}
              </Button>
            </div>
          </StandardCardContent>
        </StandardCard>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <StandardCard>
        <StandardCardHeader>
          <div className="flex items-center justify-between">
            <div>
              <StandardCardTitle>{t('admin.payments.title')}</StandardCardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {t('admin.payments.subtitle')}
              </p>
            </div>
            <Button 
              onClick={fetchPayments}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
              {t('admin.payments.refresh')}
            </Button>
          </div>
        </StandardCardHeader>
      </StandardCard>

      {/* Filters */}
      <StandardCard>
        <StandardCardHeader>
          <StandardCardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            {t('admin.payments.filters.title')}
          </StandardCardTitle>
        </StandardCardHeader>
        <StandardCardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">{t('admin.payments.filters.search')}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
                <Input
                  id="search"
                  placeholder={t('admin.payments.filters.searchPlaceholder')}
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="status">{t('admin.payments.filters.status')}</Label>
              <Select value={filters.status} onValueChange={(value) => handleFilterChange("status", value)}>
                <SelectTrigger>
                  <SelectValue placeholder={t('admin.payments.filters.statusPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t('admin.payments.filters.allStatuses')}</SelectItem>
                  <SelectItem value="SUCCESS">{t('admin.payments.status.success')}</SelectItem>
                  <SelectItem value="PENDING">{t('admin.payments.status.pending')}</SelectItem>
                  <SelectItem value="FAILED">{t('admin.payments.status.failed')}</SelectItem>
                  <SelectItem value="CANCELLED">{t('admin.payments.status.cancelled')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="from_date">{t('admin.payments.filters.fromDate')}</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
                <Input
                  id="from_date"
                  type="date"
                  value={filters.from_date}
                  onChange={(e) => handleFilterChange("from_date", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="to_date">{t('admin.payments.filters.toDate')}</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
                <Input
                  id="to_date"
                  type="date"
                  value={filters.to_date}
                  onChange={(e) => handleFilterChange("to_date", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex items-end">
              <Button 
                onClick={() => {
                  setFilters({ status: "", search: "", from_date: "", to_date: "" })
                  setCurrentPage(1)
                }}
                variant="outline"
                className="w-full"
              >
                {t('admin.payments.filters.clear')}
              </Button>
            </div>
          </div>
        </StandardCardContent>
      </StandardCard>

      {/* Payments Table */}
      <StandardCard>
        <StandardCardHeader>
          <div className="flex items-center justify-between">
            <StandardCardTitle>{t('admin.payments.table.title')}</StandardCardTitle>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              {t('admin.payments.table.showing', {
                start: ((currentPage - 1) * state.pagination.limit) + 1,
                end: Math.min(currentPage * state.pagination.limit, state.pagination.total),
                total: state.pagination.total
              })}
            </div>
          </div>
        </StandardCardHeader>
        <StandardCardContent>
          {state.loading ? (
            <TableSkeleton />
          ) : state.payments.length === 0 ? (
            <div className="text-center py-12">
              <CreditCard className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-300">{t('admin.payments.empty')}</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('admin.payments.table.paymentId')}</TableHead>
                      <TableHead>{t('admin.payments.table.orderId')}</TableHead>
                      <TableHead>{t('admin.payments.table.amount')}</TableHead>
                      <TableHead>{t('admin.payments.table.status')}</TableHead>
                      <TableHead>{t('admin.payments.table.method')}</TableHead>
                      <TableHead>{t('admin.payments.table.created')}</TableHead>
                      <TableHead>{t('admin.payments.table.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {state.payments.map((payment) => (
                      <TableRow key={payment.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                            {payment.id.substring(0, 8)}...
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="font-medium">{payment.razorpay_order_id || 'N/A'}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
                            {formatCurrency(payment.amount, payment.currency)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(payment.status)}>
                            {payment.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{payment.payment_method}</Badge>
                        </TableCell>
                        <TableCell>
                          {formatDate(payment.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => handleViewDetails(payment.id)}
                              className="flex items-center gap-2"
                            >
                              <Eye className="w-4 h-4" />
                              {t('admin.payments.actions.view')}
                            </Button>
                            {canRefund(payment.status) && (
                              <Button 
                                variant="destructive" 
                                size="sm"
                                onClick={() => {
                                  setPaymentToRefund(payment.id)
                                  setIsRefundModalOpen(true)
                                }}
                                className="flex items-center gap-2"
                              >
                                <RotateCcw className="w-4 h-4" />
                                {t('admin.payments.actions.refund')}
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="mt-6">
                <Pagination
                  currentPage={currentPage}
                  totalPages={Math.ceil(state.pagination.total / state.pagination.limit)}
                  onPageChange={setCurrentPage}
                  totalItems={state.pagination.total}
                  itemsPerPage={state.pagination.limit}
                />
              </div>
            </>
          )}
        </StandardCardContent>
      </StandardCard>

      {/* Payment Details Drawer */}
      <Drawer open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>{t('admin.payments.detail.title')}</DrawerTitle>
            <DrawerDescription>
              {selectedPayment && `${t('admin.payments.detail.payment')} #${selectedPayment.id.substring(0, 8)}...`}
            </DrawerDescription>
          </DrawerHeader>
          <div className="p-6 space-y-6">
            {selectedPayment && (
              <>
                {/* Payment Summary */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.payments.detail.amount')}</div>
                    <div className="font-bold text-lg text-green-600 dark:text-green-400">
                      {formatCurrency(selectedPayment.amount, selectedPayment.currency)}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.payments.detail.status')}</div>
                    <Badge className={getStatusColor(selectedPayment.status)}>
                      {selectedPayment.status}
                    </Badge>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.payments.detail.method')}</div>
                    <div className="font-medium">{selectedPayment.payment_method}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.payments.detail.currency')}</div>
                    <div className="font-medium">{selectedPayment.currency}</div>
                  </div>
                </div>

                {/* Payment Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">{t('admin.payments.detail.paymentInfo')}</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600 dark:text-gray-300">Payment ID:</span> {selectedPayment.id}</div>
                      <div><span className="text-gray-600 dark:text-gray-300">Order ID:</span> {selectedPayment.razorpay_order_id || 'N/A'}</div>
                      <div><span className="text-gray-600 dark:text-gray-300">Payment Method:</span> {selectedPayment.payment_method}</div>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">{t('admin.payments.detail.timeline')}</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600 dark:text-gray-300">{t('admin.payments.detail.created')}:</span> {formatDate(selectedPayment.created_at)}</div>
                      <div><span className="text-gray-600 dark:text-gray-300">{t('admin.payments.detail.updated')}:</span> {formatDate(selectedPayment.updated_at)}</div>
                    </div>
                  </div>
                </div>

                {/* Razorpay Details */}
                {selectedPayment.razorpay_payment_id && (
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">{t('admin.payments.detail.razorpayInfo')}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-300">Razorpay Order ID:</span>
                        <div className="font-mono">{selectedPayment.razorpay_order_id}</div>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-300">Razorpay Payment ID:</span>
                        <div className="font-mono">{selectedPayment.razorpay_payment_id}</div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button variant="outline">{t('admin.payments.detail.close')}</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* Refund Confirmation Modal */}
      {paymentToRefund && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900 rounded-full">
                <RotateCcw className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="font-semibold">{t('admin.payments.refund.title')}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">{t('admin.payments.refund.subtitle')}</p>
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg mb-4">
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">{t('admin.payments.refund.warning')}</p>
              <p className="font-medium">{t('admin.payments.refund.confirmation')}</p>
            </div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => {
                setIsRefundModalOpen(false)
                setPaymentToRefund(null)
              }}>
                {t('admin.payments.refund.cancel')}
              </Button>
              <Button 
                variant="destructive"
                onClick={() => handleRefund(paymentToRefund)}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {t('admin.payments.refund.confirm')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
