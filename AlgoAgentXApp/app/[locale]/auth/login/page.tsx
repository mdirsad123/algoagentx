'use client'

import React, { useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axiosInstance from '@/lib/axios'
import Toast from '@/components/shared/toast'

// Form schema
const LoginSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" })
})

type LoginFormValues = z.infer<typeof LoginSchema>

export default function LoginPage() {
  const router = useRouter()
  const params = useParams()
  const locale = params.locale as string
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(LoginSchema),
    defaultValues: {
      email: '',
      password: ''
    }
  })

  const onSubmit = async (values: LoginFormValues) => {
    try {
      setLoading(true)

      // Call FastAPI login endpoint
      const response = await axiosInstance.post('/api/v1/auth/login', {
        email: values.email,
        password: values.password
      })

      // Store tokens
      const { access_token, user } = response.data
      localStorage.setItem('access_token', access_token)
      axiosInstance.defaults.headers['Authorization'] = `Bearer ${access_token}`

      // Set cookie for middleware authentication check
      document.cookie = `accessToken=${access_token}; path=/; max-age=86400; samesite=strict`

      // TEMPORARILY DISABLE ROLE-BASED REDIRECTS - Redirect to single dashboard
      router.push(`/${locale}/dashboard`)

    } catch (error: any) {
      console.error('Login error:', error)
      Toast.fire({
        icon: 'error',
        title: 'Login failed',
        text: error.response?.data?.detail || 'Invalid credentials'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex">
      {/* Left Side - Branding Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 to-slate-800 items-center justify-center p-12">
        <div className="text-center text-white">
          <div className="mb-8">
            <Image
              src="/algoagentx_icon.jpeg"
              alt="AlgoAgentX Logo"
              width={120}
              height={120}
              className="mx-auto mb-4 rounded-lg"
            />
            <h1 className="text-3xl font-bold mb-2">AlgoAgentX</h1>
            <p className="text-slate-300 text-lg">AI-Powered Trading Intelligence</p>
          </div>

          <div className="space-y-4 text-left max-w-sm">
            <div className="flex items-center space-x-3">
              <Brain className="w-5 h-5 text-blue-400" />
              <span className="text-slate-200">Smart Algorithm Trading</span>
            </div>
            <div className="flex items-center space-x-3">
              <TrendingUp className="w-5 h-5 text-green-400" />
              <span className="text-slate-200">Data-Driven Strategies</span>
            </div>
            <div className="flex items-center space-x-3">
              <Shield className="w-5 h-5 text-yellow-400" />
              <span className="text-slate-200">Secure & Reliable</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 bg-white flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome Back</h2>
            <p className="text-slate-600">Sign in to your AlgoAgentX account</p>
          </div>

          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  className="pl-10 w-full h-11 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-colors"
                  {...form.register('email')}
                />
              </div>
              {form.formState.errors.email && (
                <p className="mt-1 text-sm text-red-600">{form.formState.errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="pl-10 pr-10 w-full h-11 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-colors"
                  {...form.register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {form.formState.errors.password && (
                <p className="mt-1 text-sm text-red-600">{form.formState.errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-slate-600 focus:ring-slate-500 border-slate-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-700">
                  Remember me
                </label>
              </div>
              <div className="text-sm">
                <a href="/auth/forgotpassword" className="font-medium text-slate-600 hover:text-slate-900">
                  Forgot password?
                </a>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-lg transition-colors"
            >
              {loading ? (
                <>
                  <ThreeDots color="#FFFFFF" height={20} width={20} />
                </>
              ) : 'Sign In'}
            </Button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-600">
            Don't have an account?{' '}
            <a href={`/${locale}/auth/signup`} className="font-medium text-slate-900 hover:text-slate-700">
              Sign up
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

// Import ThreeDots from react-loader-spinner
import { ThreeDots } from "react-loader-spinner"
import { Brain, Shield, TrendingUp } from 'lucide-react'
