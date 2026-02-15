import * as React from "react"
import { useState, useEffect } from "react"
import { useRouter, useParams } from "next/navigation"
import { toast } from "@/components/ui/use-toast"
import { NotificationProvider } from "@/contexts/notification-context"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Loader2, ArrowLeft, Save, CheckCircle } from "lucide-react"

interface StrategyRequestDetail {
  id: string
  title: string
  strategy_type: string | null
  market: string | null
  timeframe: string | null
  indicators: any | null
  entry_rules: string
  exit_rules: string
  risk_rules: string
  notes: string | null
  status: string
  user_id: string
  user_email: string | null
  user_name: string | null
  admin_notes: string | null
  assigned_to: string | null
  deployed_strategy_id: string | null
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

export default function AdminStrategyRequestDetailPage() {
  const [request, setRequest] = useState<StrategyRequestDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [userRole, setUserRole] = useState<string | null>(null)
  
  const router = useRouter()
  const params = useParams()
  const requestId = params.id as string

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

  // Fetch request details
  useEffect(() => {
    const fetchRequest = async () => {
      if (userRole !== 'admin') return
      
      try {
        setLoading(true)
        const response = await fetch(`/api/v1/admin/strategy-requests/${requestId}`)
        
        if (!response.ok) {
          throw new Error("Failed to fetch strategy request")
        }

        const data = await response.json()
        setRequest(data)
      } catch (error) {
        console.error("Error fetching strategy request:", error)
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to load strategy request details",
        })
        router.push('/admin/strategy-requests')
      } finally {
        setLoading(false)
      }
    }

    fetchRequest()
  }, [requestId, userRole, router])

  const handleUpdate = async (field: string, value: any) => {
    if (!request) return

    const updatedRequest = { ...request, [field]: value }
    setRequest(updatedRequest)
  }

  const handleSave = async () => {
    if (!request) return

    try {
      setSaving(true)
      
      const response = await fetch(`/api/v1/admin/strategy-requests/${requestId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: request.status,
          admin_notes: request.admin_notes,
          assigned_to: request.assigned_to,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to update strategy request")
      }

      const updatedRequest = await response.json()
      setRequest(updatedRequest)

      // Show success toast
      if (request.status === "DEPLOYED") {
        toast({
          title: "Strategy Deployed!",
          description: "This strategy request has been marked as deployed.",
        })
      } else {
        toast({
          title: "Updated Successfully",
          description: "Strategy request has been updated.",
        })
      }
    } catch (error) {
      console.error("Error updating strategy request:", error)
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to update strategy request",
      })
    } finally {
      setSaving(false)
    }
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

  if (userRole !== 'admin') {
    return null // Don't render anything while checking role
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    )
  }

  if (!request) {
    return (
      <div className="text-center py-8 text-gray-500">
        Strategy request not found
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button
            variant="ghost"
            onClick={() => router.push('/admin/strategy-requests')}
            className="mb-2"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Requests
          </Button>
          <h1 className="text-3xl font-bold text-gray-900">{request.title}</h1>
          <p className="text-gray-600 mt-2">
            Manage strategy request details and update status
          </p>
        </div>
        <div className="flex items-center gap-4">
          {getStatusBadge(request.status as StrategyStatus)}
          <Button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Request Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Request Details</CardTitle>
            <CardDescription>
              Information provided by the user requesting the strategy
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Strategy Type</Label>
                <div className="text-sm text-gray-600">
                  {request.strategy_type || "-"}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Market</Label>
                <div className="text-sm text-gray-600">
                  {request.market || "-"}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Timeframe</Label>
                <div className="text-sm text-gray-600">
                  {request.timeframe || "-"}
                </div>
              </div>
            </div>

            {/* Indicators */}
            {request.indicators && (
              <div className="space-y-2">
                <Label>Indicators Configuration</Label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    {JSON.stringify(request.indicators, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Rules */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Entry Rules</Label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[120px]">
                  <p className="text-sm">{request.entry_rules}</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Exit Rules</Label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[120px]">
                  <p className="text-sm">{request.exit_rules}</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Risk Management Rules</Label>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[120px]">
                  <p className="text-sm">{request.risk_rules}</p>
                </div>
              </div>

              {request.notes && (
                <div className="space-y-2">
                  <Label>Additional Notes</Label>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <p className="text-sm">{request.notes}</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Admin Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Admin Controls</CardTitle>
            <CardDescription>
              Update request status and add admin notes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status */}
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select 
                value={request.status} 
                onValueChange={(value) => handleUpdate('status', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UNDER_DEVELOPMENT">Under Development</SelectItem>
                  <SelectItem value="NEEDS_CLARIFICATION">Needs Clarification</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                  <SelectItem value="DEPLOYED">Deployed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Assigned To */}
            <div className="space-y-2">
              <Label htmlFor="assigned_to">Assigned To</Label>
              <Input
                id="assigned_to"
                placeholder="Team member name or email"
                value={request.assigned_to || ""}
                onChange={(e) => handleUpdate('assigned_to', e.target.value)}
              />
            </div>

            {/* Admin Notes */}
            <div className="space-y-2">
              <Label htmlFor="admin_notes">Admin Notes</Label>
              <Textarea
                id="admin_notes"
                placeholder="Add notes for this request..."
                value={request.admin_notes || ""}
                onChange={(e) => handleUpdate('admin_notes', e.target.value)}
                className="min-h-[120px]"
              />
            </div>

            {/* User Info */}
            <div className="space-y-4 pt-4 border-t">
              <div>
                <Label>User Information</Label>
                <div className="mt-2 space-y-1">
                  <div className="text-sm font-medium">{request.user_name || "Unknown User"}</div>
                  <div className="text-sm text-gray-600">{request.user_email || "-"}</div>
                  <div className="text-xs text-gray-500">User ID: {request.user_id}</div>
                </div>
              </div>

              <div>
                <Label>Request Timeline</Label>
                <div className="mt-2 space-y-1 text-sm text-gray-600">
                  <div>Created: {formatDate(request.created_at)}</div>
                  <div>Updated: {formatDate(request.updated_at)}</div>
                </div>
              </div>

              {request.deployed_strategy_id && (
                <div>
                  <Label>Deployed Strategy</Label>
                  <div className="mt-2 text-sm text-green-600">
                    Strategy ID: {request.deployed_strategy_id}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}