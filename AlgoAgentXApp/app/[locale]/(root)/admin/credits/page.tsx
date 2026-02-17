"use client"

import React, { useState, useEffect } from "react"
import { useTranslation } from "@/hooks/use-translations"
import { adminApi, CreditTransaction } from "@/lib/api/admin"
import { parseApiError } from "@/lib/api/error"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { StandardCard, StandardCardHeader, StandardCardTitle, StandardCardContent } from "@/components/ui/standard-card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription, DrawerFooter, DrawerClose } from "@/components/ui/drawer"
import { format } from "date-fns"
import { 
  CreditCard, 
  Search, 
  RefreshCw, 
  Eye, 
  Filter, 
  PlusCircle,
  User,
  Calendar,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  RotateCcw
} from "lucide-react"
import { LoadingSkeleton, StatsSkeleton, TableSkeleton } from "@/components/ui/loading-skeleton"
import { Pagination } from "@/components/ui/pagination"

interface FilterState {
  search: string
  from_date: string
  to_date: string
}

interface CreditPageState {
  credits: CreditTransaction[]
  loading: boolean
  error: string | null
  pagination: {
    total: number
    skip: number
    limit: number
  }
}

interface AdjustCreditsData {
  user_id: string
  amount: number
  reason: string
}

export default function AdminCreditsPage() {
  const { t } = useTranslation()
  const [state, setState] = useState<CreditPageState>({
    credits: [],
    loading: true,
    error: null,
    pagination: {
      total: 0,
      skip: 0,
      limit: 20
    }
  })
  
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    from_date: "",
    to_date: ""
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedCredit, setSelectedCredit] = useState<CreditTransaction | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [isAdjustModalOpen, setIsAdjustModalOpen] = useState(false)
  const [adjustData, setAdjustData] = useState<AdjustCreditsData>({
    user_id: "",
    amount: 0,
    reason: ""
  })
  const [isAdjusting, setIsAdjusting] = useState(false)

  const fetchCredits = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      
      const skip = (currentPage - 1) * state.pagination.limit
      
      const params: any = {
        ...(filters.search && { search: filters.search }),
        ...(filters.from_date && { from_date: filters.from_date }),
        ...(filters.to_date && { to_date: filters.to_date })
      }

      const response = await adminApi.getCredits(skip, state.pagination.limit)
      
      setState(prev => ({
        ...prev,
        credits: response.items || [],
        pagination: {
          total: response.total || 0,
          skip: skip,
          limit: state.pagination.limit
        },
        loading: false
      }))
    } catch (error) {
      const parsedError = parseApiError(error)
      const errorMessage = parsedError.message || t('admin.credits.error.fetchFailed')
      
      setState(prev => ({ ...prev, loading: false, error: errorMessage }))
    }
  }

  useEffect(() => {
    fetchCredits()
  }, [currentPage, filters])

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const handleViewDetails = (credit: CreditTransaction) => {
    setSelectedCredit(credit)
    setIsDetailOpen(true)
  }

  const handleAdjustCredits = async () => {
    if (!adjustData.user_id || !adjustData.amount || !adjustData.reason) {
      alert(t('admin.credits.adjust.validationError'))
      return
    }

    try {
      setIsAdjusting(true)
      await adminApi.adjustCredits(adjustData.user_id, adjustData.amount, adjustData.reason)
      setIsAdjustModalOpen(false)
      setAdjustData({ user_id: "", amount: 0, reason: "" })
      fetchCredits()
      alert(t('admin.credits.adjust.success'))
    } catch (error) {
      const parsedError = parseApiError(error)
      alert(parsedError.message || t('admin.credits.adjust.error'))
    } finally {
      setIsAdjusting(false)
    }
  }

  const getCreditColor = (credits: number) => {
    return credits > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
  }

  const getCreditIcon = (credits: number) => {
    return credits > 0 ? <PlusCircle className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy')
    } catch {
      return dateString
    }
  }

  if (state.loading && state.credits.length === 0) {
    return (
      <div className="space-y-6">
        <StandardCard>
          <StandardCardHeader>
            <div className="flex items-center justify-between">
              <div>
                <StandardCardTitle>{t('admin.credits.title')}</StandardCardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  {t('admin.credits.subtitle')}
                </p>
              </div>
              <Button 
                onClick={fetchCredits}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
                {t('admin.credits.refresh')}
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
            <StandardCardTitle>{t('admin.credits.title')}</StandardCardTitle>
          </StandardCardHeader>
          <StandardCardContent>
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <p className="text-red-600 dark:text-red-400 mb-4">{state.error}</p>
              <Button onClick={fetchCredits} variant="outline">
                {t('admin.credits.retry')}
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
              <StandardCardTitle>{t('admin.credits.title')}</StandardCardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {t('admin.credits.subtitle')}
              </p>
            </div>
            <div className="flex gap-2">
              <Button 
                onClick={fetchCredits}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${state.loading ? 'animate-spin' : ''}`} />
                {t('admin.credits.refresh')}
              </Button>
              <Button 
                onClick={() => setIsAdjustModalOpen(true)}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white"
              >
                <PlusCircle className="w-4 h-4" />
                {t('admin.credits.adjust.title')}
              </Button>
            </div>
          </div>
        </StandardCardHeader>
      </StandardCard>

      {/* Filters */}
      <StandardCard>
        <StandardCardHeader>
          <StandardCardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            {t('admin.credits.filters.title')}
          </StandardCardTitle>
        </StandardCardHeader>
        <StandardCardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">{t('admin.credits.filters.search')}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
                <Input
                  id="search"
                  placeholder={t('admin.credits.filters.searchPlaceholder')}
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="from_date">{t('admin.credits.filters.fromDate')}</Label>
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
              <Label htmlFor="to_date">{t('admin.credits.filters.toDate')}</Label>
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
          </div>
        </StandardCardContent>
      </StandardCard>

      {/* Credits Ledger Table */}
      <StandardCard>
        <StandardCardHeader>
          <div className="flex items-center justify-between">
            <StandardCardTitle>{t('admin.credits.table.title')}</StandardCardTitle>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              {t('admin.credits.table.showing', {
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
          ) : state.credits.length === 0 ? (
            <div className="text-center py-12">
              <CreditCard className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-300">{t('admin.credits.empty')}</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('admin.credits.table.date')}</TableHead>
                      <TableHead>{t('admin.credits.table.user')}</TableHead>
                      <TableHead>{t('admin.credits.table.amount')}</TableHead>
                      <TableHead>{t('admin.credits.table.reason')}</TableHead>
                      <TableHead>{t('admin.credits.table.admin')}</TableHead>
                      <TableHead>{t('admin.credits.table.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {state.credits.map((credit) => (
                      <TableRow key={credit.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                            {formatDate(credit.created_at)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                            <div>
                              <div className="font-medium">{credit.user_email}</div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">{credit.user_id.substring(0, 8)}...</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className={`flex items-center gap-2 font-medium ${getCreditColor(credit.credits)}`}>
                            {getCreditIcon(credit.credits)}
                            {credit.credits > 0 ? `+${credit.credits}` : credit.credits}
                            <DollarSign className="w-4 h-4" />
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-xs truncate" title={credit.reason}>
                            {credit.reason}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">System</Badge>
                        </TableCell>
                        <TableCell>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleViewDetails(credit)}
                            className="flex items-center gap-2"
                          >
                            <Eye className="w-4 h-4" />
                            {t('admin.credits.actions.view')}
                          </Button>
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

      {/* Credit Details Drawer */}
      <Drawer open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>{t('admin.credits.detail.title')}</DrawerTitle>
            <DrawerDescription>
              {selectedCredit && `${t('admin.credits.detail.transaction')} #${selectedCredit.id.substring(0, 8)}...`}
            </DrawerDescription>
          </DrawerHeader>
          <div className="p-6 space-y-6">
            {selectedCredit && (
              <>
                {/* Credit Summary */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.credits.detail.amount')}</div>
                    <div className={`font-bold text-lg ${getCreditColor(selectedCredit.credits)}`}>
                      {selectedCredit.credits > 0 ? `+${selectedCredit.credits}` : selectedCredit.credits} Credits
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.credits.detail.type')}</div>
                    <Badge variant={selectedCredit.type === 'CREDIT' ? "default" : "secondary"}>
                      {selectedCredit.type}
                    </Badge>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.credits.detail.user')}</div>
                    <div className="font-medium">{selectedCredit.user_email}</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 dark:text-gray-300">{t('admin.credits.detail.date')}</div>
                    <div className="font-medium">{formatDate(selectedCredit.created_at)}</div>
                  </div>
                </div>

                {/* Credit Details */}
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">{t('admin.credits.detail.reason')}</h4>
                  <div className="text-sm">{selectedCredit.reason}</div>
                </div>

                {/* User Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">{t('admin.credits.detail.userInfo')}</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600 dark:text-gray-300">User ID:</span> {selectedCredit.user_id}</div>
                      <div><span className="text-gray-600 dark:text-gray-300">Email:</span> {selectedCredit.user_email}</div>
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h4 className="font-semibold mb-2">{t('admin.credits.detail.timeline')}</h4>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-600 dark:text-gray-300">{t('admin.credits.detail.created')}:</span> {formatDate(selectedCredit.created_at)}</div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button variant="outline">{t('admin.credits.detail.close')}</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      {/* Adjust Credits Modal */}
      <Dialog open={isAdjustModalOpen} onOpenChange={setIsAdjustModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-green-600" />
              {t('admin.credits.adjust.title')}
            </DialogTitle>
            <DialogDescription>
              {t('admin.credits.adjust.subtitle')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="user_id">{t('admin.credits.adjust.userId')}</Label>
              <Input
                id="user_id"
                placeholder={t('admin.credits.adjust.userIdPlaceholder')}
                value={adjustData.user_id}
                onChange={(e) => setAdjustData(prev => ({ ...prev, user_id: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">{t('admin.credits.adjust.amount')}</Label>
              <div className="flex gap-2">
                <Input
                  id="amount"
                  type="number"
                  placeholder={t('admin.credits.adjust.amountPlaceholder')}
                  value={adjustData.amount || ''}
                  onChange={(e) => setAdjustData(prev => ({ ...prev, amount: parseInt(e.target.value) || 0 }))}
                />
                <Badge variant="outline" className="self-end">
                  {adjustData.amount > 0 ? t('admin.credits.adjust.credit') : adjustData.amount < 0 ? t('admin.credits.adjust.debit') : t('admin.credits.adjust.neutral')}
                </Badge>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">{t('admin.credits.adjust.reason')}</Label>
              <Input
                id="reason"
                placeholder={t('admin.credits.adjust.reasonPlaceholder')}
                value={adjustData.reason}
                onChange={(e) => setAdjustData(prev => ({ ...prev, reason: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsAdjustModalOpen(false)}
            >
              {t('admin.credits.adjust.cancel')}
            </Button>
            <Button 
              onClick={handleAdjustCredits}
              disabled={isAdjusting || !adjustData.user_id || !adjustData.amount || !adjustData.reason}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {isAdjusting ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  {t('admin.credits.adjust.processing')}
                </>
              ) : (
                <>
                  <PlusCircle className="w-4 h-4 mr-2" />
                  {t('admin.credits.adjust.confirm')}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
