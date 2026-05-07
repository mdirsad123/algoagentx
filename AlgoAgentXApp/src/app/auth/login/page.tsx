'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Eye, EyeOff, Lock, Mail, Brain, Shield, TrendingUp, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'
import GoogleAuthButton from '@/components/auth/GoogleAuthButton'
import { setAuthSession } from '@/lib/auth/session'
import { ThreeDots } from 'react-loader-spinner'

const LoginSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email' }),
  password: z.string().min(6, { message: 'Password must be at least 6 characters' }),
})

type LoginFormValues = z.infer<typeof LoginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const { showToast } = useToast()

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (values: LoginFormValues) => {
    try {
      setLoading(true)
      const response = await axiosInstance.post('/api/v1/auth/login', {
        email: values.email.trim().toLowerCase(),
        password: values.password,
        remember_me: rememberMe,
      })
      const { access_token, user } = response.data
      setAuthSession(access_token, user, { rememberMe })
      axiosInstance.defaults.headers['Authorization'] = `Bearer ${access_token}`
      showToast('Login successful!', 'success')
      router.push(user.role === 'admin' ? '/admin/dashboard' : '/dashboard')
    } catch (error: any) {
      showToast(error?.response?.data?.detail || error?.message || 'Invalid email or password', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="min-h-screen w-full flex">
        <div className="hidden lg:flex lg:w-1/2 app-gradient-bg items-center justify-center p-12">
          <div className="text-center text-white">
            <div className="mb-8">
              <Image src="/images/algoagentx_icon.jpeg" alt="AlgoAgentX Logo" width={120} height={120} className="mx-auto mb-4 rounded-xl shadow-2xl" />
              <h1 className="text-3xl font-bold mb-2 gradient-text">AlgoAgentX</h1>
              <p className="text-purple-100 text-lg">AI-Powered Trading Intelligence</p>
            </div>
            <div className="space-y-4 text-left max-w-sm">
              <div className="flex items-center gap-3"><Brain className="w-5 h-5 text-purple-300" /><span className="text-purple-100">Smart Algorithm Trading</span></div>
              <div className="flex items-center gap-3"><TrendingUp className="w-5 h-5 text-green-300" /><span className="text-purple-100">Data-Driven Strategies</span></div>
              <div className="flex items-center gap-3"><Shield className="w-5 h-5 text-blue-300" /><span className="text-purple-100">Secure & Reliable</span></div>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-1/2 flex items-center justify-center p-5 sm:p-8">
          <div className="w-full max-w-md rounded-3xl border border-white/15 bg-white/10 p-6 sm:p-8 shadow-2xl backdrop-blur-2xl">
            <div className="mb-7 text-center">
              <h2 className="text-2xl font-bold gradient-text mb-2">Welcome Back</h2>
              <p className="text-sm text-purple-100">Sign in to your AlgoAgentX account</p>
            </div>

            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-purple-100 mb-2">Email Address</label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" />
                  <Input id="email" type="email" placeholder="your@email.com" className="h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-4 text-white placeholder:text-purple-200/60 focus:border-purple-300" {...form.register('email')} />
                </div>
                {form.formState.errors.email && <p className="mt-1 text-sm text-red-300">{form.formState.errors.email.message}</p>}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-purple-100 mb-2">Password</label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-purple-200/80" />
                  <Input id="password" type={showPassword ? 'text' : 'password'} placeholder="••••••••" className="h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-12 text-white placeholder:text-purple-200/60 focus:border-purple-300" {...form.register('password')} />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200 hover:text-white" aria-label="Toggle password visibility">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {form.formState.errors.password && <p className="mt-1 text-sm text-red-300">{form.formState.errors.password.message}</p>}
              </div>

              <div className="flex items-center justify-between gap-3">
                <label className="group flex items-center gap-2 text-sm text-purple-100" title="Keep me signed in for longer on this device.">
                  <input id="remember-me" type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} className="h-4 w-4 rounded border-white/30 bg-white/10 text-purple-500 focus:ring-purple-400" />
                  <span>Remember me</span>
                  <Info className="h-3.5 w-3.5 text-purple-200/70" />
                </label>
                <a href="/auth/forgotpassword" className="text-sm font-medium text-purple-200 hover:text-white">Forgot password?</a>
              </div>

              <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white shadow-xl hover:from-fuchsia-400 hover:to-purple-400">
                {loading ? <ThreeDots color="#FFFFFF" height={20} width={40} /> : 'Sign In'}
              </Button>
            </form>

            <div className="my-6 flex items-center gap-3"><div className="h-px flex-1 bg-white/15" /><span className="text-xs font-bold uppercase tracking-[0.25em] text-purple-200">or continue with</span><div className="h-px flex-1 bg-white/15" /></div>
            <GoogleAuthButton rememberMe={rememberMe} />

            <div className="mt-7 text-center text-sm text-purple-100">Don't have an account? <a href="/auth/signup" className="font-semibold text-purple-200 hover:text-white">Sign up</a></div>
          </div>
        </div>
      </div>
    </AuthShell>
  )
}
