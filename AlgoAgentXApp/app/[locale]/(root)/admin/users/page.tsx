"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Users, Search, RefreshCw, Eye, EyeOff, UserPlus } from "lucide-react"
import { adminApi, User } from "@/lib/api/admin"
import { AdminTable } from "@/components/admin/admin-table"
import { toast } from "sonner"
import { parseApiError, formatErrorMessage } from "@/lib/api/error"
import EmptyState from "@/components/shared/empty-state"

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [skip, setSkip] = useState(0)
  const [limit] = useState(20)
  const [total, setTotal] = useState(0)

  const fetchUsers = async (newSkip?: number) => {
    try {
      setLoading(true)
      setError(null)
      const skipValue = newSkip !== undefined ? newSkip : skip
      const result = await adminApi.getUsers(skipValue, limit, search)
      setUsers(result.items)
      setTotal(result.total)
      if (newSkip !== undefined) setSkip(newSkip)
    } catch (err) {
      console.error("Error fetching users:", err)
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
    setSkip(0) // Reset to first page when searching
    // Debounce the search to avoid too many API calls
    setTimeout(() => {
      fetchUsers(0)
    }, 300)
  }

  const handleUserStatusToggle = async (user: User) => {
    try {
      const newStatus = !user.is_active
      await adminApi.updateUserStatus(user.id, newStatus)
      toast.success(`User ${newStatus ? 'activated' : 'deactivated'} successfully`)
      // Refresh the current page
      fetchUsers()
    } catch (err) {
      console.error("Error updating user status:", err)
      const errorInfo = parseApiError(err);
      toast.error(formatErrorMessage(errorInfo))
    }
  }

  const handleRefresh = () => {
    fetchUsers()
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const columns = [
    {
      key: 'email' as const,
      label: 'Email',
      render: (email: string) => (
        <div className="font-medium">{email}</div>
      )
    },
    {
      key: 'role' as const,
      label: 'Role',
      render: (role: string) => (
        <Badge variant={role === 'admin' ? "destructive" : "default"}>
          {role.toUpperCase()}
        </Badge>
      )
    },
    {
      key: 'is_active' as const,
      label: 'Status',
      render: (isActive: boolean) => (
        <Badge variant={isActive ? "default" : "secondary"}>
          {isActive ? "Active" : "Inactive"}
        </Badge>
      )
    },
    {
      key: 'created_at' as const,
      label: 'Created At',
      render: (date: string) => (
        <div className="text-sm text-gray-500">
          {new Date(date).toLocaleDateString()}
        </div>
      )
    },
    {
      key: 'updated_at' as const,
      label: 'Last Updated',
      render: (date: string) => (
        <div className="text-sm text-gray-500">
          {new Date(date).toLocaleDateString()}
        </div>
      )
    }
  ]

  const actions = [
    {
      label: 'Toggle Status',
      onClick: handleUserStatusToggle,
      variant: "outline" as const,
      icon: <Eye className="h-4 w-4" />
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">Manage users, view details, and control access</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button>
            <UserPlus className="mr-2 h-4 w-4" />
            Add User
          </Button>
        </div>
      </div>

      <AdminTable<User>
        title="Users"
        columns={columns}
        data={users}
        loading={loading}
        error={error}
        onRefresh={handleRefresh}
        onSearch={handleSearch}
        searchPlaceholder="Search users by email..."
        emptyMessage="No users found"
        actions={actions}
      />

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {skip + 1} - {Math.min(skip + limit, total)} of {total} users
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => fetchUsers(Math.max(0, skip - limit))}
              disabled={skip === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => fetchUsers(skip + limit)}
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