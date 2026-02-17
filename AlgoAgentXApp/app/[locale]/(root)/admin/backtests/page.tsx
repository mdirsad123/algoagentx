"use client"

import React, { useState, useEffect } from "react"
import { useUser } from "@/contexts/user-context"
import { toast } from "sonner"
import { withLocale } from "@/lib/route"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { format } from "date-fns"
import { ru } from "date-fns/locale"
import { 
  Search, 
  Calendar, 
  Filter, 
  Eye, 
  RefreshCw,
  TrendingUp,
  TrendingDown,
  BarChart3,
  User,
  DollarSign,
  Target,
  Shield
} from "lucide-react"
import { LoadingSkeleton } from "@/components/ui/loading-skeleton"
import { Pagination } from "@/components/ui/pagination"

interface Backtest {
  id: string
  strategy_id: string
  strategy_name: string
  user_id: string
  user_email: string
  user_name: string
  total_return: number
  sharpe_ratio: number
  max_drawdown: number
  created_at: string
  updated_at: string
}

interface PaginationInfo {
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function AdminBacktestsPage() {
  const { user } = useUser()
  const [backtests, setBacktests] = useState<Backtest[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState<PaginationInfo>({
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1
  })
  
  // Filters
  const [filters, setFilters] = useState({
    search: "",
    from_date: "",
    to_date: ""
  })
  
  const [currentPage, setCurrentPage] = useState(1)

  const fetchBacktests = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pagination.page_size.toString(),
        ...(filters.search && { search: filters.search }),
        ...(filters.from_date && { from_date: filters.from_date }),
        ...(filters.to_date && { to_date: filters.to_date })
      })

      const response = await fetch(`/api/v1/admin/backtests?${params}`)
      if (!response.ok) {
        throw new Error("Failed to fetch backtests")
      }
      
      const data = await response.json()
      setBacktests(data.items || [])
      setPagination({
        total: data.total || 0,
        page: data.page || 1,
        page_size: data.page_size || 20,
        total_pages: data.total_pages || 1
      })
    } catch (error) {
      console.error("Error fetching backtests:", error)
      toast.error("Failed to load backtests")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBacktests()
  }, [currentPage, filters])

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const getPerformanceColor = (returnPercent: number) => {
    if (returnPercent > 0) return "text-green-600 dark:text-green-400"
    if (returnPercent < 0) return "text-red-600 dark:text-red-400"
    return "text-gray-600 dark:text-gray-400"
  }

  const getPerformanceIcon = (returnPercent: number) => {
    if (returnPercent > 0) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (returnPercent < 0) return <TrendingDown className="h-4 w-4 text-red-600" />
    return <BarChart3 className="h-4 w-4 text-gray-600" />
  }

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatRatio = (value: number) => {
    return value.toFixed(2)
  }

  if (loading && backtests.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <LoadingSkeleton className="h-8 w-64" />
            <LoadingSkeleton className="h-4 w-96" />
          </div>
          <LoadingSkeleton className="h-10 w-32" />
        </div>
        
        <Card>
          <CardHeader>
            <LoadingSkeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {[1, 2, 3, 4].map(i => (
                <LoadingSkeleton key={i} className="h-20 w-full" />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
              {[1, 2, 3].map(i => (
                <LoadingSkeleton key={i} className="h-32 w-full" />
              ))}
            </div>
            <LoadingSkeleton className="h-96 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Backtests Management</h1>
          <p className="text-muted-foreground">
            Monitor and analyze all strategy backtest results
          </p>
        </div>
        <Button 
          onClick={fetchBacktests}
          variant="outline"
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by strategy name, user email, or ID..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="from_date">From Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
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
              <Label htmlFor="to_date">To Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="to_date"
                  type="date"
                  value={filters.to_date}
                  onChange={(e) => handleFilterChange("to_date", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex items-end space-y-2">
              <Button 
                onClick={() => {
                  setFilters({ search: "", from_date: "", to_date: "" })
                  setCurrentPage(1)
                }}
                variant="outline"
                className="w-full"
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backtests Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Backtest Results</CardTitle>
            <div className="text-sm text-muted-foreground">
              Showing {((pagination.page - 1) * pagination.page_size) + 1} - {Math.min(pagination.page * pagination.page_size, pagination.total)} of {pagination.total} backtests
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <LoadingSkeleton className="h-96 w-full" />
          ) : backtests.length === 0 ? (
            <div className="text-center py-12">
              <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No backtests found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Strategy</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Total Return</TableHead>
                      <TableHead>Sharpe Ratio</TableHead>
                      <TableHead>Max Drawdown</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backtests.map((backtest) => (
                      <TableRow key={backtest.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Target className="h-4 w-4 text-muted-foreground" />
                            {backtest.strategy_name}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <div>
                              <div className="font-medium">{backtest.user_name}</div>
                              <div className="text-sm text-muted-foreground">{backtest.user_email}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className={`flex items-center gap-2 font-medium ${getPerformanceColor(backtest.total_return)}`}>
                            {getPerformanceIcon(backtest.total_return)}
                            {formatPercentage(backtest.total_return)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Shield className="h-4 w-4 text-blue-600" />
                            <span className="font-medium">{formatRatio(backtest.sharpe_ratio)}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <DollarSign className="h-4 w-4 text-red-600" />
                            <span className="font-medium text-red-600 dark:text-red-400">{formatPercentage(backtest.max_drawdown)}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {format(new Date(backtest.created_at), 'PPp', { locale: ru })}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => window.location.href = withLocale(window.location.pathname, `/admin/backtests/${backtest.id}`)}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </Button>
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
                  currentPage={pagination.page}
                  totalPages={pagination.total_pages}
                  onPageChange={setCurrentPage}
                  totalItems={pagination.total}
                  itemsPerPage={pagination.page_size}
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}