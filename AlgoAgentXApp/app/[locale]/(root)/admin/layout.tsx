"use client"

import React from "react"
import { useUser } from "@/contexts/user-context"
import { toast } from "sonner"
import { useRouter, usePathname } from "next/navigation"
import { withLocale } from "@/lib/route"

// Admin Sidebar Component
const AdminSidebar = React.memo(function AdminSidebar() {
  const pathname = usePathname()

  const adminMenuItems = [
    { label: "Dashboard", href: "/admin/dashboard", icon: "📊" },
    { label: "Users", href: "/admin/users", icon: "👥" },
    { label: "Payments", href: "/admin/payments", icon: "💳" },
    { label: "Subscriptions", href: "/admin/subscriptions", icon: "🔄" },
    { label: "Credits", href: "/admin/credits", icon: "💎" },
    { label: "Support Tickets", href: "/admin/support-tickets", icon: "🎫" },
  ]

  const isActive = (href: string) => {
    const currentPath = pathname.replace(/\/$/, '')
    const targetPath = href.replace(/\/$/, '')
    return currentPath === targetPath || currentPath.startsWith(targetPath + '/')
  }

  return (
    <aside className="w-[260px] min-h-screen border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col">
      {/* LOGO */}
      <div className="h-[90px] flex items-center justify-center border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-700 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">A</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">Admin</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">AlgoAgentX</p>
          </div>
        </div>
      </div>

      {/* MENU */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {adminMenuItems.map((item) => (
          <a
            key={item.href}
            href={withLocale(pathname, item.href)}
            className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors duration-200 ${
              isActive(item.href)
                ? "bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border-r-2 border-red-600 dark:border-red-500"
                : "text-gray-700 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-gray-800 hover:text-red-600 dark:hover:text-red-400"
            }`}
          >
            <span className="text-lg">{item.icon}</span>
            <span className="text-sm font-medium">{item.label}</span>
          </a>
        ))}
      </nav>

      {/* FOOTER */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <a
          href={withLocale(pathname, "/dashboard")}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-gray-800 hover:text-red-600 dark:hover:text-red-400 transition-colors duration-200"
        >
          <span className="text-lg">🏠</span>
          <span className="text-sm font-medium">Back to Dashboard</span>
        </a>
      </div>
    </aside>
  )
})

// Admin Header Component
const AdminHeader = React.memo(function AdminHeader() {
  return (
    <div className="w-full bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between h-14 px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
          <span className="px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs font-medium rounded-full">
            Admin
          </span>
        </div>
        
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Welcome to Admin Panel
        </div>
      </div>
    </div>
  )
})

export default function AdminLayout({
  children,
  params: { locale },
}: Readonly<{
  children: React.ReactNode
  params: { locale: string }
}>) {
  const { user, isLoading } = useUser()
  const router = useRouter()
  const pathname = usePathname()

  // Access control
  React.useEffect(() => {
    if (!isLoading) {
      if (!user) {
        // User not loaded yet, wait
        return
      }
      
      if (user.role !== "admin") {
        toast.error("Not authorized")
        router.push(withLocale(pathname, "/dashboard"))
      }
    }
  }, [user, isLoading, router, pathname])

  // Show loading while checking permissions
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Checking permissions...</p>
        </div>
      </div>
    )
  }

  // Don't render admin layout if not authorized
  if (user?.role !== "admin") {
    return null
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <AdminSidebar />
      
      <main className="flex-1 w-full bg-background min-h-screen relative overflow-x-hidden">
        <AdminHeader />
        
        <div className="overflow-y-auto hide-scrollbar bg-white mt-3 flex-1 mx-2 sm:mx-4 lg:ml-4 lg:mr-0">
          <div className="p-3 sm:p-4 md:p-6 dark:bg-gray-800 min-h-full">
            <div className="animate-in fade-in-0 slide-in-from-right-1 duration-300">
              {children}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}