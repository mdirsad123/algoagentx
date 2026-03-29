'use client'

import React, { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { LoadingSkeleton } from '@/components/ui/loading-skeleton'

type Props = {
  children: React.ReactNode
  requireAdmin?: boolean
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return m ? decodeURIComponent(m[2]) : null
}

export default function AuthGate({ children, requireAdmin = false }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = getCookie('accessToken') || (typeof window !== 'undefined' ? localStorage.getItem('access_token') : null)
    if (!token) {
      router.replace(`/auth/login?redirect=${encodeURIComponent(pathname)}`)
      return
    }

    if (requireAdmin) {
      const role = getCookie('loggedinuserroleid') || ''
      // backend seems to return role string (e.g., 'admin') in user.role cookie in some flows.
      // accept either 'admin' or '1' as admin.
      const isAdmin = role === 'admin' || role === '1'
      if (!isAdmin) {
        router.replace('/dashboard')
        return
      }
    }

    setReady(true)
  }, [pathname, requireAdmin, router])

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <LoadingSkeleton className="h-12 w-48 mx-auto rounded" />
          <LoadingSkeleton className="h-4 w-64 mx-auto rounded" />
          <div className="flex justify-center">
            <LoadingSkeleton className="h-8 w-8 rounded-full animate-spin border-2 border-gray-300 border-t-purple-600" />
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
