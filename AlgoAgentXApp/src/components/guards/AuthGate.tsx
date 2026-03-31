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
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]+)'))
  return m ? decodeURIComponent(m[1]) : null
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

    const storedUser = typeof window !== 'undefined' ? localStorage.getItem('currentUser') : null
    let storedRole = ''
    if (storedUser) {
      try {
        storedRole = JSON.parse(storedUser)?.role || ''
      } catch {}
    }

    if (requireAdmin) {
      const role = (getCookie('loggedinuserroleid') || getCookie('loggedinuserrole') || storedRole || '').toLowerCase()
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
