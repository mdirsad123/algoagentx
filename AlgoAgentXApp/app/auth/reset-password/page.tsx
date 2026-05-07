'use client'

import React, { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { Eye, EyeOff, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'

export default function ResetPasswordPage() {
  const router = useRouter()
  const params = useSearchParams()
  const token = params.get('token') || ''
  const { showToast } = useToast()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    if (!token) return setError('Reset token is missing or invalid.')
    if (password.length < 8) return setError('Password must be at least 8 characters.')
    if (password !== confirm) return setError('Passwords do not match.')
    setLoading(true)
    try {
      await axiosInstance.post('/api/v1/auth/reset-password', { token, new_password: password })
      showToast('Password reset successful. Please login.', 'success')
      router.push('/auth/login?reset=success')
    } catch (error: any) {
      setError(error?.response?.data?.detail || error?.message || 'Invalid or expired reset token.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = 'h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-12 text-white placeholder:text-purple-200/60'

  return (
    <AuthShell>
      <div className="min-h-screen w-full flex items-center justify-center p-5 bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
        <div className="w-full max-w-md rounded-3xl border border-white/15 bg-white/10 p-6 sm:p-8 shadow-2xl backdrop-blur-2xl">
          <div className="mb-7 text-center">
            <Image src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX" width={82} height={82} className="mx-auto mb-4 rounded-xl" />
            <h1 className="text-2xl font-bold gradient-text">Reset Password</h1>
            <p className="mt-2 text-sm text-purple-100">Create a new secure password for your account.</p>
          </div>
          <form onSubmit={submit} className="space-y-5">
            <div><label className="mb-2 block text-sm font-semibold text-purple-100">New Password</label><div className="relative"><Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" /><Input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Minimum 8 characters" className={inputClass} /><button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></div>
            <div><label className="mb-2 block text-sm font-semibold text-purple-100">Confirm Password</label><div className="relative"><Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" /><Input type={showConfirm ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Confirm password" className={inputClass} /><button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200">{showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></div>
            {error && <div className="rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}
            <Button disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white">{loading ? 'Resetting…' : 'Reset Password'}</Button>
          </form>
          <a href="/auth/login" className="mt-6 block text-center text-sm font-semibold text-purple-200 hover:text-white">Back to Login</a>
        </div>
      </div>
    </AuthShell>
  )
}
