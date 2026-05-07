'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { ArrowLeft, Eye, EyeOff, Info, Lock, Mail, RefreshCw, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'
import { setAuthSession } from '@/lib/auth/session'
import { ThreeDots } from 'react-loader-spinner'

const LoginSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email' }),
  password: z.string().min(6, { message: 'Password must be at least 6 characters' }),
})

type LoginValues = z.infer<typeof LoginSchema>
type Step = 'password' | 'otp'

const ADMIN_OTP_CHALLENGE_KEY = 'algoagentx_admin_otp_challenge'

const maskEmail = (email: string) => {
  const [name, domain] = email.split('@')
  if (!name || !domain) return email
  const first = name.slice(0, 1)
  const last = name.length > 2 ? name.slice(-1) : ''
  return `${first}${'*'.repeat(Math.max(3, name.length - 2))}${last}@${domain}`
}

const getApiMessage = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return err?.message || fallback
}

export default function AdminLoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('password')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [otpLoading, setOtpLoading] = useState(false)
  const [resendLoading, setResendLoading] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [otp, setOtp] = useState('')
  const [otpSessionId, setOtpSessionId] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [resendSeconds, setResendSeconds] = useState(0)
  const [otpError, setOtpError] = useState('')
  const otpInputRef = useRef<HTMLInputElement | null>(null)
  const { showToast } = useToast()

  const form = useForm<LoginValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: '', password: '' },
  })

  useEffect(() => {
    if (typeof window === 'undefined') return
    const rawChallenge = window.sessionStorage.getItem(ADMIN_OTP_CHALLENGE_KEY)
    if (!rawChallenge) return

    try {
      const challenge = JSON.parse(rawChallenge)
      const sessionId = String(challenge?.otp_session_id || '')
      const email = String(challenge?.email || '')
      if (!sessionId || !email) {
        window.sessionStorage.removeItem(ADMIN_OTP_CHALLENGE_KEY)
        return
      }

      setOtpSessionId(sessionId)
      setAdminEmail(email)
      setRememberMe(Boolean(challenge?.remember_me))
      setResendSeconds(Number(challenge?.resend_cooldown_seconds || 60))
      setOtp('')
      setOtpError('')
      setStep('otp')
      form.setValue('email', email)
    } catch {
      window.sessionStorage.removeItem(ADMIN_OTP_CHALLENGE_KEY)
    }
  }, [form])

  const maskedEmail = useMemo(() => maskEmail(adminEmail), [adminEmail])

  useEffect(() => {
    if (step !== 'otp') return
    const focusTimer = window.setTimeout(() => otpInputRef.current?.focus(), 100)
    return () => window.clearTimeout(focusTimer)
  }, [step])

  useEffect(() => {
    if (step !== 'otp' || resendSeconds <= 0) return
    const timer = window.setInterval(() => {
      setResendSeconds((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [step, resendSeconds])

  const completeAdminLogin = (accessToken: string, user: any) => {
    if (!accessToken || !user || (user.role !== 'admin' && user.role !== '1')) {
      showToast('You are not authorized for admin access', 'error')
      return
    }
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(ADMIN_OTP_CHALLENGE_KEY)
    }
    setAuthSession(accessToken, user, { rememberMe })
    axiosInstance.defaults.headers['Authorization'] = `Bearer ${accessToken}`
    showToast('Welcome Admin!', 'success')
    router.push('/admin/dashboard')
  }

  const onSubmit = async (values: LoginValues) => {
    try {
      setLoading(true)
      setOtpError('')
      const email = values.email.trim().toLowerCase()
      const response = await axiosInstance.post('/api/v1/auth/login', {
        email,
        password: values.password,
        remember_me: rememberMe,
      })

      if (response.data?.requires_otp) {
        const sessionId = response.data?.otp_session_id
        if (!sessionId) {
          showToast('OTP session was not created. Please try again.', 'error')
          return
        }
        setOtpSessionId(sessionId)
        setAdminEmail(email)
        setOtp('')
        const cooldownSeconds = Number(response.data?.resend_cooldown_seconds || 60)
        setResendSeconds(cooldownSeconds)
        if (typeof window !== 'undefined') {
          window.sessionStorage.setItem(ADMIN_OTP_CHALLENGE_KEY, JSON.stringify({
            otp_session_id: sessionId,
            email,
            remember_me: rememberMe,
            resend_cooldown_seconds: cooldownSeconds,
            created_at: Date.now(),
          }))
        }
        setStep('otp')
        showToast(response.data?.message || 'OTP sent to admin email', 'success')
        return
      }

      completeAdminLogin(response.data?.access_token, response.data?.user)
    } catch (err: any) {
      showToast(getApiMessage(err, 'Admin login failed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async (event?: React.FormEvent) => {
    event?.preventDefault()
    const cleanOtp = otp.replace(/\D/g, '').slice(0, 6)
    if (cleanOtp.length !== 6) {
      setOtpError('Please enter the 6-digit OTP.')
      return
    }
    try {
      setOtpLoading(true)
      setOtpError('')
      const response = await axiosInstance.post('/api/v1/auth/admin/verify-otp', {
        otp_session_id: otpSessionId,
        otp: cleanOtp,
        remember_me: rememberMe,
      })
      completeAdminLogin(response.data?.access_token, response.data?.user)
    } catch (err: any) {
      const msg = getApiMessage(err, 'Invalid or expired OTP.')
      setOtpError(msg)
      showToast(msg, 'error')
      const lower = msg.toLowerCase()
      if (lower.includes('max') || lower.includes('locked') || lower.includes('too many')) {
        window.setTimeout(() => resetToPasswordStep(), 1200)
      }
    } finally {
      setOtpLoading(false)
    }
  }

  const resendOtp = async () => {
    if (!otpSessionId || resendSeconds > 0) return
    try {
      setResendLoading(true)
      setOtpError('')
      const response = await axiosInstance.post('/api/v1/auth/admin/resend-otp', {
        otp_session_id: otpSessionId,
      })
      const cooldown = Number(response.data?.resend_cooldown_seconds || response.data?.cooldown_seconds || 60)
      setResendSeconds(cooldown)
      setOtp('')
      showToast(response.data?.message || 'OTP resent to admin email', 'success')
    } catch (err: any) {
      const msg = getApiMessage(err, 'Unable to resend OTP.')
      setOtpError(msg)
      showToast(msg, 'error')
    } finally {
      setResendLoading(false)
    }
  }

  const resetToPasswordStep = () => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(ADMIN_OTP_CHALLENGE_KEY)
    }
    setStep('password')
    setOtp('')
    setOtpError('')
    setOtpSessionId('')
    setAdminEmail('')
    setResendSeconds(0)
  }

  return (
    <AuthShell>
      <div className="min-h-screen w-full flex">
        <div className="hidden lg:flex lg:w-1/2 app-gradient-bg items-center justify-center p-12">
          <div className="text-center text-white">
            <div className="mb-8">
              <Image src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX Logo" width={120} height={120} className="mx-auto mb-4 rounded-xl shadow-2xl" />
              <h1 className="text-3xl font-bold mb-2 gradient-text">AlgoAgentX</h1>
              <p className="text-purple-100 text-lg">Secure Admin Console</p>
            </div>
            <div className="mx-auto max-w-sm space-y-4 text-left">
              <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-purple-300" /><span className="text-purple-100">Email OTP protected access</span></div>
              <div className="flex items-center gap-3"><Lock className="h-5 w-5 text-blue-300" /><span className="text-purple-100">Password + second verification</span></div>
              <div className="flex items-center gap-3"><Mail className="h-5 w-5 text-green-300" /><span className="text-purple-100">Admin Google login disabled</span></div>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-1/2 flex items-center justify-center p-5 sm:p-8">
          <div className="w-full max-w-md rounded-3xl border border-white/15 bg-white/10 p-6 sm:p-8 shadow-2xl backdrop-blur-2xl">
            {step === 'password' ? (
              <>
                <div className="mb-7 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-purple-300/30 bg-purple-500/20 shadow-xl">
                    <ShieldCheck className="h-7 w-7 text-purple-100" />
                  </div>
                  <h2 className="text-2xl font-bold gradient-text mb-2">Admin Login</h2>
                  <p className="text-sm text-purple-100">Admin accounts require email OTP.</p>
                </div>

                <div className="mb-5 rounded-2xl border border-purple-300/20 bg-purple-500/10 p-4 text-sm text-purple-100">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-purple-200" />
                    <div>
                      <p className="font-semibold text-white">Extra verification enabled</p>
                      <p className="mt-1 text-purple-100/80">Enter your admin password once. We will send one OTP to your email.</p>
                    </div>
                  </div>
                </div>

                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                  <div>
                    <label htmlFor="admin-email" className="block text-sm font-semibold text-purple-100 mb-2">Email Address</label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" />
                      <Input id="admin-email" type="email" placeholder="admin@company.com" className="h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-4 text-white placeholder:text-purple-200/60 focus:border-purple-300" {...form.register('email')} />
                    </div>
                    {form.formState.errors.email && <p className="mt-1 text-sm text-red-300">{form.formState.errors.email.message}</p>}
                  </div>

                  <div>
                    <label htmlFor="admin-password" className="block text-sm font-semibold text-purple-100 mb-2">Password</label>
                    <div className="relative">
                      <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" />
                      <Input id="admin-password" type={showPassword ? 'text' : 'password'} placeholder="••••••••" className="h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-12 text-white placeholder:text-purple-200/60 focus:border-purple-300" {...form.register('password')} />
                      <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200 hover:text-white" aria-label="Toggle password visibility">
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                    {form.formState.errors.password && <p className="mt-1 text-sm text-red-300">{form.formState.errors.password.message}</p>}
                  </div>

                  <label className="group flex items-center gap-2 text-sm text-purple-100" title="Keep this admin session active longer on this trusted device.">
                    <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} className="h-4 w-4 rounded border-white/30 bg-white/10 text-purple-500 focus:ring-purple-400" />
                    <span>Remember me</span>
                    <Info className="h-3.5 w-3.5 text-purple-200/70" />
                  </label>

                  <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white shadow-xl hover:from-fuchsia-400 hover:to-purple-400">
                    {loading ? <ThreeDots color="#FFFFFF" height={20} width={40} /> : 'Sign In'}
                  </Button>
                </form>
              </>
            ) : (
              <>
                <div className="mb-7 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-purple-300/30 bg-purple-500/20 shadow-xl">
                    <Mail className="h-7 w-7 text-purple-100" />
                  </div>
                  <h2 className="text-2xl font-bold gradient-text mb-2">Verify Admin OTP</h2>
                  <p className="text-sm text-purple-100">Enter the 6-digit code sent to your admin email.</p>
                </div>

                <div className="mb-5 rounded-2xl border border-purple-300/20 bg-purple-500/10 p-4 text-sm text-purple-100">
                  <p className="font-semibold text-white">We sent a 6-digit OTP to your admin email.</p>
                  <p className="mt-1 text-purple-100/80">{maskedEmail}</p>
                </div>

                <form onSubmit={verifyOtp} className="space-y-5">
                  <div>
                    <label htmlFor="admin-otp" className="block text-sm font-semibold text-purple-100 mb-2">Admin OTP</label>
                    <Input
                      ref={otpInputRef}
                      id="admin-otp"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="000000"
                      maxLength={6}
                      value={otp}
                      onChange={(event) => {
                        setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))
                        setOtpError('')
                      }}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && otp.length === 6) verifyOtp(event as any)
                      }}
                      className="h-14 w-full rounded-xl border-white/15 bg-white/10 text-center text-2xl font-bold tracking-[0.45em] text-white placeholder:text-purple-200/40 focus:border-purple-300"
                    />
                    {otpError ? <p className="mt-2 text-sm text-red-300">{otpError}</p> : <p className="mt-2 text-xs text-purple-100/70">OTP expires in 10 minutes. Never share this code with anyone.</p>}
                  </div>

                  <Button type="submit" disabled={otpLoading || otp.length !== 6} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white shadow-xl hover:from-fuchsia-400 hover:to-purple-400">
                    {otpLoading ? <ThreeDots color="#FFFFFF" height={20} width={40} /> : 'Verify OTP & Open Admin'}
                  </Button>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <Button type="button" variant="outline" className="h-11 rounded-xl border-white/15 bg-white/5 text-purple-100 hover:bg-white/10 hover:text-white" onClick={resetToPasswordStep} disabled={otpLoading}>
                      <ArrowLeft className="mr-2 h-4 w-4" /> Change email
                    </Button>
                    <Button type="button" variant="outline" className="h-11 rounded-xl border-white/15 bg-white/5 text-purple-100 hover:bg-white/10 hover:text-white" onClick={resendOtp} disabled={resendLoading || resendSeconds > 0}>
                      <RefreshCw className={`mr-2 h-4 w-4 ${resendLoading ? 'animate-spin' : ''}`} />
                      {resendSeconds > 0 ? `Resend in ${resendSeconds}s` : resendLoading ? 'Resending...' : 'Resend OTP'}
                    </Button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </AuthShell>
  )
}
