'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Eye, EyeOff, Lock, Mail, User, Brain, Shield, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { ThreeDots } from "react-loader-spinner"
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'

// Form schema
const SignupSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email" }),
  fullname: z.string().optional(),
  mobile: z.string().optional(),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
  confirmPassword: z.string().min(6, { message: "Please confirm your password" })
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"]
})

type SignupFormValues = z.infer<typeof SignupSchema>

export default function SignupPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const form = useForm<SignupFormValues>({
    resolver: zodResolver(SignupSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      fullname: '',
      mobile: ''
    }
  })

  const { showToast } = useToast()

  const onSubmit = async (values: SignupFormValues) => {
    try {
      setLoading(true)

      // Call AlgoAgentX API signup endpoint
      const response = await axiosInstance.post('/api/v1/auth/signup', {
        email: values.email,
        password: values.password,
        fullname: values.fullname,
        mobile: values.mobile
      })

      showToast('Account created successfully!', 'success')

      // Redirect to login page
      router.push('/auth/login')

    } catch (error: any) {
      console.error('Signup error:', error)
      showToast(error.response?.data?.detail || 'An error occurred during signup', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="min-h-screen w-full flex">
        {/* Left Side - Branding Panel */}
        <div className="hidden lg:flex lg:w-1/2 app-gradient-bg items-center justify-center p-12">
          <div className="text-center text-white">
              <div className="mb-8">
              <Image
                src="/images/algoagentx_icon.jpeg"
                alt="AlgoAgentX Logo"
                width={120}
                height={120}
                className="mx-auto mb-4 rounded-lg"
              />
              <h1 className="text-3xl font-bold mb-2 gradient-text">AlgoAgentX</h1>
              <p className="text-purple-200 text-lg">AI-Powered Trading Intelligence</p>
            </div>

            <div className="space-y-4 text-left max-w-sm">
              <div className="flex items-center space-x-3">
                <Brain className="w-5 h-5 text-purple-400" />
                <span className="text-purple-200">Smart Algorithm Trading</span>
              </div>
              <div className="flex items-center space-x-3">
                <TrendingUp className="w-5 h-5 text-green-400" />
                <span className="text-purple-200">Data-Driven Strategies</span>
              </div>
              <div className="flex items-center space-x-3">
                <Shield className="w-5 h-5 text-blue-400" />
                <span className="text-purple-200">Secure & Reliable</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Signup Form */}
        <div className="w-full lg:w-1/2 bg-transparent flex items-center justify-center p-8">
          <div className="w-full max-w-md glass-card p-8 depth-3">
            <div className="mb-8 text-center">
              <h2 className="text-2xl font-bold gradient-text mb-2">Create Your Account</h2>
              <p className="text-purple-200">Join AlgoAgentX and start trading smarter</p>
            </div>

            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

              <div>
                <label htmlFor="fullname" className="block text-sm font-medium text-purple-200 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-300" />
                  <Input
                    id="fullname"
                    type="text"
                    placeholder="Your full name"
                    className="pl-10 w-full h-11 glass-input rounded-lg"
                    {...form.register('fullname')}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="mobile" className="block text-sm font-medium text-purple-200 mb-1">
                  Mobile Number
                </label>
                <div className="relative">
                  <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <Input
                    id="mobile"
                    type="tel"
                    placeholder="+91 98765 43210"
                    className="pl-10 w-full h-11 glass-input rounded-lg"
                    {...form.register('mobile')}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-purple-200 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-300" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    className="pl-10 w-full h-11 glass-input rounded-lg"
                    {...form.register('email')}
                  />
                </div>
                {form.formState.errors.email && (
                  <p className="mt-1 text-sm text-red-400">{form.formState.errors.email.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-purple-200 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-300" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className="pl-10 pr-10 w-full h-11 glass-input rounded-lg"
                    {...form.register('password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-purple-300 hover:text-purple-100"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {form.formState.errors.password && (
                  <p className="mt-1 text-sm text-red-400">{form.formState.errors.password.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-purple-200 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-purple-300" />
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className="pl-10 pr-10 w-full h-11 glass-input rounded-lg"
                    {...form.register('confirmPassword')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-purple-300 hover:text-purple-100"
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {form.formState.errors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-400">{form.formState.errors.confirmPassword.message}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full h-11 glass-button text-white font-medium rounded-lg"
              >
                {loading ? (
                  <>
                    <ThreeDots color="#FFFFFF" height={20} width={20} />
                  </>
                ) : 'Create Account'}
              </Button>
            </form>

            <div className="mt-8 text-center text-sm text-purple-200">
              Already have an account?{' '}
              <a href="/auth/login" className="font-medium text-purple-300 hover:text-purple-100">
                Sign in
              </a>
            </div>
          </div>
        </div>
      </div>
    </AuthShell>
  )
}
