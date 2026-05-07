'use client'

import React, { useState } from 'react'
import Image from 'next/image'
import { Mail, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [devLink, setDevLink] = useState('')
  const { showToast } = useToast()

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setDevLink('')
    try {
      const res = await axiosInstance.post('/api/v1/auth/forgot-password', { email: email.trim().toLowerCase() })
      setMessage(res.data?.message || 'If this email exists, password reset instructions have been sent.')
      if (res.data?.dev_reset_link) setDevLink(res.data.dev_reset_link)
      showToast('Password reset request submitted.', 'success')
    } catch (error: any) {
      setMessage('If this email exists, password reset instructions have been sent.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="min-h-screen w-full flex items-center justify-center p-5 bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
        <div className="w-full max-w-md rounded-3xl border border-white/15 bg-white/10 p-6 sm:p-8 shadow-2xl backdrop-blur-2xl">
          <div className="mb-7 text-center">
            <Image src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX" width={82} height={82} className="mx-auto mb-4 rounded-xl" />
            <h1 className="text-2xl font-bold gradient-text">Forgot Password</h1>
            <p className="mt-2 text-sm text-purple-100">Enter your email and we will send reset instructions.</p>
          </div>
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-purple-100">Email Address</label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" />
                <Input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="your@email.com" className="h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-4 text-white placeholder:text-purple-200/60" />
              </div>
            </div>
            <Button disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white">{loading ? 'Sending…' : 'Send Reset Link'}</Button>
          </form>
          {message && <div className="mt-5 rounded-xl border border-green-400/20 bg-green-500/10 p-3 text-sm text-green-100">{message}</div>}
          {devLink && <a href={devLink} className="mt-3 block break-all rounded-xl border border-yellow-400/20 bg-yellow-500/10 p-3 text-xs text-yellow-100">Dev reset link: {devLink}</a>}
          <a href="/auth/login" className="mt-6 flex items-center justify-center gap-2 text-sm font-semibold text-purple-200 hover:text-white"><ArrowLeft size={16} /> Back to Login</a>
        </div>
      </div>
    </AuthShell>
  )
}
