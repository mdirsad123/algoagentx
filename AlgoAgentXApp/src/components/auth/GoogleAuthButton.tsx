'use client'

import React, { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import { setAuthSession } from '@/lib/auth/session'

declare global {
  interface Window {
    google?: any
  }
}

type Props = {
  rememberMe?: boolean
  className?: string
}

const GOOGLE_SCRIPT_ID = 'google-identity-services-script'

export default function GoogleAuthButton({ rememberMe = false, className = '' }: Props) {
  const router = useRouter()
  const { showToast } = useToast()
  const buttonRef = useRef<HTMLDivElement | null>(null)
  const [loading, setLoading] = useState(false)
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''

  useEffect(() => {
    if (!clientId || !buttonRef.current) return

    const initialize = () => {
      if (!window.google || !buttonRef.current) return
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response: any) => {
            if (!response?.credential) {
              showToast('Google login failed. Please try again.', 'error')
              return
            }
            try {
              setLoading(true)
              const res = await axiosInstance.post('/api/v1/auth/google', {
                credential: response.credential,
                remember_me: rememberMe,
              })
              const { access_token, user } = res.data
              setAuthSession(access_token, user, { rememberMe })
              axiosInstance.defaults.headers['Authorization'] = `Bearer ${access_token}`
              showToast('Google login successful!', 'success')
              router.push(user?.role === 'admin' ? '/admin/dashboard' : '/dashboard')
            } catch (error: any) {
              showToast(error?.response?.data?.detail || error?.message || 'Google login failed', 'error')
            } finally {
              setLoading(false)
            }
          },
        })
        buttonRef.current.innerHTML = ''
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          width: Math.min(420, buttonRef.current.offsetWidth || 360),
          text: 'continue_with',
          shape: 'rectangular',
        })
      } catch (error) {
        console.error('Google button init failed', error)
      }
    }

    if (window.google) {
      initialize()
      return
    }

    let script = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null
    if (!script) {
      script = document.createElement('script')
      script.id = GOOGLE_SCRIPT_ID
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      document.head.appendChild(script)
    }
    script.addEventListener('load', initialize)
    return () => script?.removeEventListener('load', initialize)
  }, [clientId, rememberMe, router, showToast])

  if (!clientId) {
    return (
      <button type="button" disabled className={`h-11 w-full rounded-xl border border-white/10 bg-white/10 text-sm text-purple-200 opacity-60 ${className}`}>
        Google login not configured
      </button>
    )
  }

  return (
    <div className={`relative h-11 w-full overflow-hidden rounded-xl bg-white shadow-sm ${className}`}>
      {loading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 text-sm text-slate-700">Verifying Google…</div>}
      <div ref={buttonRef} className="flex h-11 w-full items-center justify-center overflow-hidden rounded-xl" />
    </div>
  )
}
