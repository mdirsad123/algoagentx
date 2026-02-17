"use client"

import React, { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { toast } from "sonner"
import { useUser } from "@/contexts/user-context"
import { LoadingSkeleton } from "@/components/ui/loading-skeleton"
import { withLocale } from "@/lib/route"

interface RouteGuardProps {
  children: React.ReactNode
  requireAuth?: boolean
  requireAdmin?: boolean
}

export default function RouteGuard({ 
  children, 
  requireAuth = false, 
  requireAdmin = false 
}: RouteGuardProps) {
  const { user, isLoading } = useUser()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    // If still loading user data, show skeleton
    if (isLoading) {
      return
    }

    // Check authentication requirement
    if (requireAuth && !user) {
      // Redirect to login with locale preservation
      const loginUrl = withLocale(pathname, "/auth/login")
      router.replace(loginUrl)
      return
    }

    // Check admin requirement (only if user is authenticated)
    if (requireAdmin && user && user.role !== "admin") {
      // Show error toast and redirect to dashboard
      toast.error("Not authorized", {
        description: "You need admin privileges to access this page."
      })
      const dashboardUrl = withLocale(pathname, "/dashboard")
      router.replace(dashboardUrl)
      return
    }
  }, [user, isLoading, requireAuth, requireAdmin, router, pathname])

  // Show loading skeleton while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <LoadingSkeleton className="h-12 w-48 mx-auto rounded" />
          <LoadingSkeleton className="h-4 w-64 mx-auto rounded" />
          <div className="flex justify-center">
            <LoadingSkeleton className="h-8 w-8 rounded-full animate-spin border-2 border-gray-300 border-t-red-600" />
          </div>
        </div>
      </div>
    )
  }

  // If authentication is required but user is not authenticated, don't render children
  if (requireAuth && !user) {
    return null
  }

  // If admin is required but user is not admin, don't render children
  if (requireAdmin && user && user.role !== "admin") {
    return null
  }

  // Render children if all checks pass
  return <>{children}</>
}