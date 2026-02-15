import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { toast } from "@/components/ui/use-toast"
import { NotificationProvider } from "@/contexts/notification-context"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Loader2, Search, Eye, Filter } from "lucide-react"

interface StrategyRequest {
  id: string
  title: string
  strategy_type: string | null
  market: string | null
  timeframe: string | null
  status: string
  user_id: string
  user_email: string | null
  user_name: string | null
  created_at: string
  updated_at: string
}

type StrategyStatus = "UNDER_DEVELOPMENT" | "NEEDS_CLARIFICATION" | "REJECTED" | "DEPLOYED"

const statusConfig = {
  UNDER_DEVELOPMENT: {
    label: "Under Development",
    color: "bg-blue-100 text-blue-800",
  },
  NEEDS_CLARIFICATION: {
    label: "Needs Clarification",
    color: "bg-yellow-100 text-yellow-800",
  },
  REJECTED: {
    label: "Rejected",
    color: "bg-red-100 text-red-800",
  },
  DEPLOYED: {
    label: "Deployed",
    color: "bg-green-100 text-green-800",
  },
}

export default function AdminStrategyRequestsPage() {
  const [requests, setRequests] = useState<StrategyRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<StrategyStatus | "all">("all")
  const [userRole, setUserRole] = useState<string | null>(null)
  
  const router = useRouter()

  // Check user role
  useEffect(() => {
    const checkUserRole = () => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('access_token')
        if (token) {
          try {
            const payload = JSON.parse(atob(token.split('.')[1]))
            setUserRole(payload.role)
            
            // Redirect if not admin
            if (payload.role !== 'admin') {
              router.push('/403')
            }
          } catch (e) {
            router.push('/auth/login')
          }
        } else {
          router.push('/auth/login')
        }
      }
    }
    
    checkUserRole()
  }, [router])

  // Fetch requests
  useEffect(() => {
    const fetchRequests = async () => {
      if (userRole !== 'admin') return
      
      try {
        setLoading(true)
        const response = await fetch("/api/v1/admin/strategy-requests")
        
        if (!response.ok) {
          throw new Error("Failed to fetch strategy requests")
        }

        const data = await response.json()
        setRequests(data)
      } catch (error) {
        console.error("Error fetching strategy requests:", error)
        setError("Unable to load strategy requests")
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to load strategy requests",
        })
      } finally {
        setLoading(false)
      }
    }

    fetchRequests()
  }, [userRole])

  const handleViewDetails = (requestId: string) => {
    router.push(`/admin/strategy-requests/${requestId}`)
  }

  const getStatusBadge = (status: StrategyStatus) => {
    const config = statusConfig[status]
    
    return (
      <Badge className={config.color}>
        {config.label}
      </Badge>
    )
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

  // Filter requests
  const filteredRequests = requests.filter(request => {
    const matchesSearch = request.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (request.user_name && request.user_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
                         (request.user_email && request.user_email.toLowerCase().includes(searchTerm.toLowerCase()))
    
    const matchesStatus = statusFilter === "all" || request.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  if (userRole !== 'admin') {
    return null // Don't render anything while checking role
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Strategy Requests</h1>
        <p className="text-gray-600 mt-2">
          Manage and review custom strategy requests from users
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Request Management</CardTitle>
          <CardDescription>
            View and manage all strategy requests submitted by users
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1">
              <Label htmlFor="search" className="sr-only">
                Search
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  id="search"
                  placeholder="Search by title, user name, or email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="w-full sm:w-64">
              <Label htmlFor="status-filter">Filter by Status</Label>
              <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StrategyStatus | "all")}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="UNDER_DEVELOPMENT">Under Development</SelectItem>
                  <SelectItem value="NEEDS_CLARIFICATION">Needs Clarification</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                  <SelectItem value="DEPLOYED">Deployed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
          ) : error ? (
            <div className="text-red-500 text-center py-8">{error}</div>
          ) : filteredRequests.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No strategy requests found
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[300px]">Title</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Market</TableHead>
                    <TableHead>Timeframe</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRequests.map((request) => (
                    <TableRow key={request.id} className="hover:bg-gray-50">
                      <TableCell className="font-medium">
                        {request.title}
                      </TableCell>
                      <TableCell>
                        {request.strategy_type || "-"}
                      </TableCell>
                      <TableCell>
                        {request.market || "-"}
                      </TableCell>
                      <TableCell>
                        {request.timeframe || "-"}
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(request.status as StrategyStatus)}
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{request.user_name || "Unknown"}</div>
                          <div className="text-sm text-gray-500">{request.user_email || "-"}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {formatDate(request.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewDetails(request.id)}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}