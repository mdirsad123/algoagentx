'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { LoadingSkeleton } from '@/components/ui/loading-skeleton'
import { clearAuthSession } from '@/lib/auth/session'

type Props = {
  children: React.ReactNode
  requireAdmin?: boolean
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]+)'))
  return m ? decodeURIComponent(m[1]) : null
}

function getToken(): string | null {
  return getCookie('accessToken') || (typeof window !== 'undefined' ? localStorage.getItem('access_token') : null)
}

function decodeJwtPayload(token: string): Record<string, any> | null {
  try {
    const part = token.split('.')[1]
    if (!part) return null
    const normalized = part.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=')
    return JSON.parse(window.atob(padded))
  } catch {
    return null
  }
}

function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return false
  return Number(payload.exp) * 1000 <= Date.now() + 5000
}

function getStoredRole(): string {
  const storedUser = typeof window !== 'undefined' ? localStorage.getItem('currentUser') : null
  if (storedUser) {
    try {
      return String(JSON.parse(storedUser)?.role || '').toLowerCase()
    } catch {}
  }
  return String(getCookie('loggedinuserroleid') || getCookie('loggedinuserrole') || '').toLowerCase()
}

export default function AuthGate({ children, requireAdmin = false }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(false)

  const loginRedirect = useMemo(() => {
    const target = pathname || (requireAdmin ? '/admin/dashboard' : '/dashboard')
    const loginPath = requireAdmin || target.startsWith('/admin') ? '/auth/admin-login' : '/auth/login'
    return `${loginPath}?redirect=${encodeURIComponent(target)}`
  }, [pathname, requireAdmin])

  useEffect(() => {
    const token = getToken()
    if (!token || isTokenExpired(token)) {
      clearAuthSession()
      router.replace(loginRedirect)
      return
    }

    const role = getStoredRole()
    const isAdmin = role === 'admin' || role === '1'

    if (requireAdmin && !isAdmin) {
      router.replace('/dashboard')
      return
    }

    if (!requireAdmin && isAdmin && pathname && !pathname.startsWith('/admin')) {
      router.replace('/admin/dashboard')
      return
    }

    if (requireAdmin && pathname && !pathname.startsWith('/admin') && pathname !== '/auth/admin-login') {
      router.replace('/admin/dashboard')
      return
    }

    setReady(true)
  }, [loginRedirect, pathname, requireAdmin, router])

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#120826] via-[#4a178f] to-[#1a2448]">
        <div className="space-y-4 text-center">
          <LoadingSkeleton className="mx-auto h-12 w-48 rounded" />
          <LoadingSkeleton className="mx-auto h-4 w-64 rounded" />
          <div className="flex justify-center">
            <LoadingSkeleton className="h-8 w-8 rounded-full animate-spin border-2 border-gray-300 border-t-purple-600" />
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
