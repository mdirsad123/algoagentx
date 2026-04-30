'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Lock, Mail, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'

const Schema = z.object({
  email: z.string().email({ message: "Please enter a valid email" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" })
})

type Values = z.infer<typeof Schema>

export default function AdminLoginPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const { showToast } = useToast()

  const form = useForm<Values>({
    resolver: zodResolver(Schema),
    defaultValues: { email: '', password: '' }
  })

  const onSubmit = async (values: Values) => {
    try {
      setLoading(true)
      const response = await axiosInstance.post('/api/v1/auth/login', values)

      const { access_token, user } = response.data
      if (!user || (user.role !== 'admin' && user.role !== '1')) {
        showToast('You are not authorized for admin access', 'error')
        return
      }

      localStorage.setItem('access_token', access_token)
      localStorage.setItem('currentUser', JSON.stringify(user))
      axiosInstance.defaults.headers['Authorization'] = `Bearer ${access_token}`

      document.cookie = `accessToken=${access_token}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinuserroleid=${user.role}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinuserid=${user.id}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinusername=${user.email}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinuseremail=${user.email}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinuserfullname=${encodeURIComponent(user.full_name || user.fullname || '')}; path=/; max-age=86400; samesite=strict`
      document.cookie = `loggedinuserrole=${user.role}; path=/; max-age=86400; samesite=strict`

      showToast('Welcome Admin!', 'success')
      router.push('/admin/dashboard')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Admin login failed'
      showToast(msg, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Admin Login"
      subtitle="Secure access to admin console"
      icon={<Shield className="h-6 w-6 text-purple-300" />}
    >
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <div className="space-y-2">
          <label className="text-sm text-white/80">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/50" />
            <Input
              type="email"
              placeholder="admin@company.com"
              className="pl-10"
              {...form.register('email')}
            />
          </div>
          {form.formState.errors.email && (
            <p className="text-xs text-red-300">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm text-white/80">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/50" />
            <Input
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••"
              className="pl-10 pr-10"
              {...form.register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {form.formState.errors.password && (
            <p className="text-xs text-red-300">{form.formState.errors.password.message}</p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in as Admin'}
        </Button>
      </form>
    </AuthShell>
  )
}
