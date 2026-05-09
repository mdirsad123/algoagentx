"use client"

import React from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, RefreshCw } from "lucide-react"
import EmptyState from "@/components/shared/empty-state";

interface AdminTableProps<T> {
  title: string
  columns: Array<{
    key: keyof T
    label: string
    render?: (value: any, item: T) => React.ReactNode
  }>
  data: T[]
  loading: boolean
  error: string | null
  onRefresh: () => void
  onSearch?: (search: string) => void
  searchPlaceholder?: string
  emptyMessage?: string
  actions?: Array<{
    label: string
    onClick: (item: T) => void
    variant?: "default" | "outline" | "secondary" | "destructive"
    icon?: React.ReactNode
  }>
}

export function AdminTable<T>({
  title,
  columns,
  data,
  loading,
  error,
  onRefresh,
  onSearch,
  searchPlaceholder = "Search...",
  emptyMessage = "No data available",
  actions = []
}: AdminTableProps<T>) {
  const [search, setSearch] = React.useState("")

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearch(value)
    if (onSearch) {
      onSearch(value)
    }
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4 text-rose-100 shadow-xl">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <Button onClick={onRefresh} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <div className="text-4xl mb-2">⚠️</div>
            <h3 className="text-lg font-semibold mb-2 text-white">Error Loading Data</h3>
            <p className="text-rose-100/80 mb-4">{error}</p>
            <Button onClick={onRefresh}>Try Again</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold text-white">{title}</h2>
        <div className="admin-action-bar">
          {onSearch && (
            <div className="relative w-full sm:w-auto">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder={searchPlaceholder}
                value={search}
                onChange={handleSearch}
                className="w-full border-white/10 bg-white/5 pl-10 text-white placeholder:text-purple-100/50 sm:w-72"
              />
            </div>
          )}
          <Button onClick={onRefresh} variant="outline" disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="admin-table-scroll rounded-2xl border border-white/10 bg-white/[0.04] shadow-xl shadow-purple-950/20 backdrop-blur-xl">
        <Table className="admin-data-table">
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={String(column.key)}>{column.label}</TableHead>
              ))}
              {actions.length > 0 && <TableHead>Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              // Loading skeleton
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}>
                  {columns.map((_, colIndex) => (
                    <TableCell key={colIndex}>
                      <div className="h-4 rounded bg-white/10 animate-pulse"></div>
                    </TableCell>
                  ))}
                  {actions.length > 0 && (
                    <TableCell>
                      <div className="h-8 rounded bg-white/10 animate-pulse w-16"></div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length + (actions.length > 0 ? 1 : 0)} className="py-10">
                  <EmptyState
                    title="No Data Available"
                    description={emptyMessage}
                    icon={<Search className="w-12 h-12 text-purple-200/60" />}
                    actionLabel="Refresh"
                    onAction={onRefresh}
                  />
                </TableCell>
              </TableRow>
            ) : (
              data.map((item, index) => (
                <TableRow key={index}>
                  {columns.map((column) => (
                    <TableCell key={String(column.key)}>
                      {column.render 
                        ? column.render(item[column.key], item)
                        : String(item[column.key] || "-")
                      }
                    </TableCell>
                  ))}
                  {actions.length > 0 && (
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        {actions.map((action, actionIndex) => (
                          <Button
                            key={actionIndex}
                            variant={action.variant || "outline"}
                            size="sm"
                            onClick={() => action.onClick(item)}
                          >
                            {action.icon && <span className="mr-2">{action.icon}</span>}
                            {action.label}
                          </Button>
                        ))}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}