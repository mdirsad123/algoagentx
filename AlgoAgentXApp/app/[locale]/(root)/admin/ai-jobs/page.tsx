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
  Bot,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  User
} from "lucide-react"
import { LoadingSkeleton } from "@/components/ui/loading-skeleton"
import { Pagination } from "@/components/ui/pagination"

interface AIJob {
  id: string
  user_id: string
  user_email: string
  user_name: string
  job_type: string
  status: string
  progress: number
  message: string
  created_at: string
  updated_at: string
}

interface PaginationInfo {
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function AdminAIJobsPage() {
  const { user } = useUser()
  const [jobs, setJobs] = useState<AIJob[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState<PaginationInfo>({
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1
  })
  
  // Filters
  const [filters, setFilters] = useState({
    status: "",
    search: "",
    from_date: "",
    to_date: ""
  })
  
  const [currentPage, setCurrentPage] = useState(1)

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pagination.page_size.toString(),
        ...(filters.status && { status: filters.status }),
        ...(filters.search && { search: filters.search }),
        ...(filters.from_date && { from_date: filters.from_date }),
        ...(filters.to_date && { to_date: filters.to_date })
      })

      const response = await fetch(`/api/v1/admin/ai-jobs?${params}`)
      if (!response.ok) {
        throw new Error("Failed to fetch AI jobs")
      }
      
      const data = await response.json()
      setJobs(data.items || [])
      setPagination({
        total: data.total || 0,
        page: data.page || 1,
        page_size: data.page_size || 20,
        total_pages: data.total_pages || 1
      })
    } catch (error) {
      console.error("Error fetching AI jobs:", error)
      toast.error("Failed to load AI jobs")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [currentPage, filters])

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed": return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
      case "running": return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
      case "pending": return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
      case "failed": return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
      default: return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
    }
  }

  const getJobIcon = (jobType: string) => {
    switch (jobType.toLowerCase()) {
      case "ai_screener": return <Bot className="h-4 w-4" />
      default: return <Bot className="h-4 w-4" />
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed": return <CheckCircle className="h-4 w-4 text-green-600" />
      case "running": return <Play className="h-4 w-4 text-blue-600" />
      case "pending": return <Clock className="h-4 w-4 text-yellow-600" />
      case "failed": return <XCircle className="h-4 w-4 text-red-600" />
      default: return <Clock className="h-4 w-4 text-gray-600" />
    }
  }

  if (loading && jobs.length === 0) {
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
          <h1 className="text-3xl font-bold tracking-tight">AI Jobs Management</h1>
          <p className="text-muted-foreground">
            Monitor and manage all AI-powered jobs and processes
          </p>
        </div>
        <Button 
          onClick={fetchJobs}
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by user email or job ID..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange("search", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={filters.status} onValueChange={(value) => handleFilterChange("status", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
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
                  setFilters({ status: "", search: "", from_date: "", to_date: "" })
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

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>AI Jobs</CardTitle>
            <div className="text-sm text-muted-foreground">
              Showing {((pagination.page - 1) * pagination.page_size) + 1} - {Math.min(pagination.page * pagination.page_size, pagination.total)} of {pagination.total} jobs
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <LoadingSkeleton className="h-96 w-full" />
          ) : jobs.length === 0 ? (
            <div className="text-center py-12">
              <Bot className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No AI jobs found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job ID</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <TableRow key={job.id}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {getJobIcon(job.job_type)}
                            {job.id.substring(0, 8)}...
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <div>
                              <div className="font-medium">{job.user_name}</div>
                              <div className="text-sm text-muted-foreground">{job.user_email}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{job.job_type}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(job.status)}
                            <Badge className={getStatusColor(job.status)}>
                              {job.status}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                              <div 
                                className="bg-blue-600 h-2 rounded-full" 
                                style={{ width: `${job.progress}%` }}
                              ></div>
                            </div>
                            <span className="text-sm font-medium">{job.progress}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-xs truncate" title={job.message}>
                            {job.message}
                          </div>
                        </TableCell>
                        <TableCell>
                          {format(new Date(job.created_at), 'PPp', { locale: ru })}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => window.location.href = withLocale(window.location.pathname, `/admin/ai-jobs/${job.id}`)}
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