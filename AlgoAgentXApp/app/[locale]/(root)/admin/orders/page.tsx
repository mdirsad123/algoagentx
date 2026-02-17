"use client"

import React, { useState, useEffect } from "react"
import { useTranslation } from "@/hooks/use-translations"
import { adminApi, type Order, type OrderItem } from "@/lib/api/admin"
import { parseApiError } from "@/lib/api/error"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardContent } from "@/components/ui/standard-card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription, DrawerFooter, DrawerClose } from "@/components/ui/drawer"
import { format } from "date-fns"
import { 
  Search, 
  Calendar, 
  Filter, 
  Eye, 
  Edit, 
  RefreshCw,
  CreditCard,
  Package,
  DollarSign,
  User,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle
} from "lucide-react"
import { LoadingSkeleton, StatsSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton"
import { Pagination } from "@/components/ui/pagination"

interface OrderDetails extends Order {
  items: OrderItem[]
}

interface FilterState {
  status: string
  search: string
  from_date: string
  to_date: string
}

interface OrderPageState {
  orders: Order[]
  loading: boolean
  error: string | null
  pagination: {
    total: number
    page: number
    page_size: number
    total_pages: number
  }
}

export default function AdminOrdersPage() {
  const { t } = useTranslation()
  const [state, setState] = useState<OrderPageState>({
    orders: [],
    loading: true,
    error: null,
    pagination: {
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1
    }
  })
  
  const [filters, setFilters] = useState<FilterState>({
    status: "",
    search: "",
    from_date: "",
    to_date: ""
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedOrder, setSelectedOrder] = useState<OrderDetails | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false)
  const [statusToUpdate, setStatusToUpdate] = useState<string | null>(null)
  const [orderToUpdate, setOrderToUpdate] = useState<string | null>(null)

  const fetchOrders = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      
      const params: any = {
        page: currentPage,
        page_size: state.pagination.page_size,
        ...(filters.status && { status: filters.status }),
        ...(filters.search && { search: filters.search }),
        ...(filters.from_date && { from_date: filters.from_date }),
        ...(filters.to_date && { to_date: filters.to_date })
      }

      const response = await adminApi.getOrders(
        params.page,
        params.page_size,
        params.status,
        params.search,
        params.from_date,
        params.to_date
      )
      
      setState(prev => ({
        ...prev,
        orders: response.items || [],
        pagination: {
          total: response.total || 0,
          page: response.page || 1,
          page_size: response.page_size || 20,
          total_pages: response.total_pages || 1
        },
        loading: false
      }))
    } catch (error) {
      const parsedError = parseApiError(error)
      const errorMessage = parsedError.message || t('admin.orders.error.fetchFailed')
      
      setState(prev => ({ ...prev, loading: false, error: errorMessage }))
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [currentPage, filters])

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const handleViewDetails = async (orderId: string) => {
    try {
      const orderDetails = await adminApi.getOrder(orderId)
      setSelectedOrder(orderDetails)
      setIsDetailOpen(true)
    } catch (error) {
      const parsedError = parseApiError(error)
      alert(parsedError.message || t('admin.orders.error.fetchOrderFailed'))
    }
  }

  const handleStatusUpdate = async (orderId: string, newStatus: string) => {
    try {
      await adminApi.updateOrderStatus(orderId, newStatus)
      setIsStatusModalOpen(false)
      setStatusToUpdate(null)
      setOrderToUpdate(null)
      fetchOrders()
    } catch (error) {
      const parsedError = parseApiError(error)
      alert(parsedError.message || t('admin.orders.error.updateStatusFailed'))
    }
  }

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase()
    if (statusLower.includes('completed') || statusLower.includes('paid')) {
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    }
    if (statusLower.includes('processing') || statusLower.includes('pending')) {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
    }
    if (statusLower.includes('cancelled') || statusLower.includes('failed')) {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    }
    if (statusLower.includes('refunded')) {
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
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

  const getTotalItems = (items: OrderItem[]) => {
    return items.reduce((total, item) => total + item.quantity, 0)
  }

  if (state.loading && state.orders.length === 0) {
    return (
      <div className="space-y-6">
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardTitle>{t('admin.orders.title')}</StandardCardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {t('admin.orders.subtitle')}
                </p>
              </div>
              <Button 
                onClick={fetchOrders}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
                {t('admin.orders.refresh')}
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
            <StandardCardTitle>{t('admin.orders.title')}</StandardCardTitle>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <p className="text-red-600 dark:text-red-400 mb-4">{state.error}</p>
              <Button onClick={fetchOrders} variant="outline">
                {t('admin.orders.retry')}
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
              <StandardCardTitle>{t('admin.orders.title')}</StandardCardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {t('admin.orders.subtitle')}
              </p>
            </div>
            <Button 
              onClick={fetchOrders}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
              {t('admin.orders.refresh')}
            </Button>
          </div>
        </StandardCardHeader>
      </StandardCard>

      {/* Filters */}
      <StandardCard>
        <StandardCardHeader>
          <StandardCardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            {t('admin.orders.filters.title')}
          </StandardCardTitle>
        </StandardCardHeader>
        <StandardCardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">{t('admin.orders.filters.search')}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
                <Input
                  id="search"
                  placeholder={t('admin.orders.filters.searchPlaceholder')}
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="status">{t('admin.orders.filters.status')}</Label>
              <Select value={filters.status} onValueChange={(value) => handleFilterChange("status", value)}>
                <SelectTrigger>
                  <SelectValue placeholder={t('admin.orders.filters.statusPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t('admin.orders.filters.allStatuses')}</SelectItem>
                  <SelectItem value="pending">{t('admin.orders.status.pending')}</SelectItem>
                  <SelectItem value="processing">{t('admin.orders.status.processing')}</SelectItem>
                  <SelectItem value="completed">{t('admin.orders.status.completed')}</SelectItem>
                  <SelectItem value="cancelled">{t('admin.orders.status.cancelled')}</SelectItem>
                  <SelectItem value="refunded">{t('admin.orders.status.refunded')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="from_date">{t('admin.orders.filters.fromDate')}</Label>
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
              <Label htmlFor="to_date">{t('admin.orders.filters.toDate')}</Label>
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
                {t('admin.orders.filters.clear')}
              </Button>
            </div>
          </div>
        </StandardCardContent>
      </StandardCard>

      {/* Orders Table */}
      <StandardCard>
        <StandardCardHeader>
          <div className="flex items-center justify-between">
            <StandardCardTitle>{t('admin.orders.table.title')}</StandardCardTitle>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              {t('admin.orders.table.showing', {
                start: ((state.pagination.page - 1) * state.pagination.page_size) + 1,
                end: Math.min(state.pagination.page * state.pagination.page_size, state.pagination.total),
                total: state.pagination.total
              })}
            </div>
          </div>
        </StandardCardHeader>
        <StandardCardContent>
          {state.loading ? (
            <TableSkeleton />
          ) : state.orders.length === 0 ? (
            <div className="text-center py-12">
              <Package className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-300">{t('admin.orders.empty')}</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('admin.orders.table.orderId')}</TableHead>
                      <TableHead>{t('admin.orders.table.customer')}</TableHead>
                      <TableHead>{t('admin.orders.table.status')}</TableHead>
                      <TableHead>{t('admin.orders.table.amount')}</TableHead>
                      <TableHead>{t('admin.orders.table.paymentMethod')}</TableHead>
                      <TableHead>{t('admin.orders.table.created')}</TableHead>
                      <TableHead>{t('admin.orders.table.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {state.orders.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Package className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                            {order.order_number}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium text-gray-900 dark:text-white">{order.user_name}</div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">{order.user_email}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(order.status)}>
                            {order.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
                            {formatCurrency(order.total_amount, order.currency)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <CreditCard className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                            {order.payment_method}
                          </div>
                        </TableCell>
                        <TableCell>
                          {formatDate(order.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => handleViewDetails(order.id)}
                              className="flex items-center gap-2"
                            >
                              <Eye className="w-4 h-4" />
                              {t('admin.orders.actions.view')}
                            </Button>
                            <Select 
                              value={order.status} 
                              onValueChange={(value) => {
                                setOrderToUpdate(order.id)
                                setStatusToUpdate(value)
                                setIsStatusModalOpen(true)
                              }}
                            >
                              <SelectTrigger className="w-32">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="pending">{t('admin.orders.status.pending')}</SelectItem>
                                <SelectItem value="processing">{t('admin.orders.status.processing')}</SelectItem>
                                <SelectItem value="completed">{t('admin.orders.status.completed')}</SelectItem>
                                <SelectItem value="cancelled">{t('admin.orders.status.cancelled')}</SelectItem>
                                <SelectItem value="refunded">{t('admin.orders.status.refunded')}</SelectItem>
                              </SelectContent>
                            </Select>
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
                  currentPage={state.pagination.page}
                  totalPages={state.pagination.total_pages}
                  onPageChange={setCurrentPage}
                  totalItems={state.pagination.total}
                  itemsPerPage={state.pagination.page_size}
                />
              </div>
            </>
          )}
        </StandardCardContent>
      </StandardCard>

      {/* Order Details Drawer */}
      <Drawer open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>{t('admin.orders.detail.title')}</DrawerTitle>
            <DrawerDescription>
              {selectedOrder && `${t('admin.orders.detail.order')} #${selectedOrder.order_number}`}
            </DrawerDescription>
          </DrawerHeader>
          <div className="p-6 space-y-6">
            {selectedOrder && (
              <>
                {/* Order Summary */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.detail.customer')}</div>
                    <div className="font-medium text-gray-900 dark:text-white">{selectedOrder.user_name}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{selectedOrder.user_email}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.detail.status')}</div>
                    <Badge className={getStatusColor(selectedOrder.status)}>
                      {selectedOrder.status}
                    </Badge>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.detail.total')}</div>
                    <div className="font-bold text-lg text-green-600 dark:text-green-400">
                      {formatCurrency(selectedOrder.total_amount, selectedOrder.currency)}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.detail.payment')}</div>
                    <div className="font-medium">{selectedOrder.payment_method}</div>
                  </div>
                </div>

                {/* Order Items */}
                <div>
                  <h4 className="text-lg font-semibold mb-4">{t('admin.orders.detail.items')}</h4>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t('admin.orders.detail.item')}</TableHead>
                          <TableHead>{t('admin.orders.detail.type')}</TableHead>
                          <TableHead>{t('admin.orders.detail.quantity')}</TableHead>
                          <TableHead>{t('admin.orders.detail.unitPrice')}</TableHead>
                          <TableHead>{t('admin.orders.detail.total')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedOrder.items.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell className="font-medium">{item.product_name || item.product_type}</TableCell>
                            <TableCell>
                              <Badge variant="secondary">{item.product_type}</Badge>
                            </TableCell>
                            <TableCell>{item.quantity}</TableCell>
                            <TableCell>{formatCurrency(item.unit_price, selectedOrder.currency)}</TableCell>
                            <TableCell>{formatCurrency(item.total_price, selectedOrder.currency)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                {/* Order Timeline */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300 mb-2">{t('admin.orders.detail.created')}</div>
                    <div className="font-medium">{formatDate(selectedOrder.created_at)}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300 mb-2">{t('admin.orders.detail.updated')}</div>
                    <div className="font-medium">{formatDate(selectedOrder.updated_at)}</div>
                  </div>
                </div>
              </>
            )}
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button variant="outline">{t('admin.orders.detail.close')}</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* Status Update Modal */}
      <Dialog open={isStatusModalOpen} onOpenChange={setIsStatusModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.orders.statusUpdate.title')}</DialogTitle>
            <DialogDescription>
              {t('admin.orders.statusUpdate.description')}
            </DialogDescription>
          </DialogHeader>
          {orderToUpdate && statusToUpdate && (
            <div className="space-y-4">
              <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.statusUpdate.current')}</span>
                  <Badge className={getStatusColor(state.orders.find(o => o.id === orderToUpdate)?.status || '')}>
                    {state.orders.find(o => o.id === orderToUpdate)?.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-sm text-gray-600 dark:text-gray-300">{t('admin.orders.statusUpdate.new')}</span>
                  <Badge className={getStatusColor(statusToUpdate)}>
                    {statusToUpdate}
                  </Badge>
                </div>
              </div>
              <div className="flex gap-3 justify-end">
                <Button variant="outline" onClick={() => setIsStatusModalOpen(false)}>
                  {t('admin.orders.statusUpdate.cancel')}
                </Button>
                <Button 
                  onClick={() => handleStatusUpdate(orderToUpdate, statusToUpdate)}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {t('admin.orders.statusUpdate.confirm')}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
