'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Eye, EyeOff, Lock, Mail, User, Phone, Brain, Shield, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { ThreeDots } from 'react-loader-spinner'
import axiosInstance from '@/lib/axios'
import { useToast } from '@/components/shared/toast'
import AuthShell from '@/components/auth/AuthShell'
import GoogleAuthButton from '@/components/auth/GoogleAuthButton'

const SignupSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email' }),
  fullname: z.string().optional(),
  mobile: z.string().optional(),
  password: z.string().min(8, { message: 'Password must be at least 8 characters' }),
  confirmPassword: z.string().min(8, { message: 'Please confirm your password' }),
}).refine((data) => data.password === data.confirmPassword, { message: 'Passwords do not match', path: ['confirmPassword'] })

type SignupFormValues = z.infer<typeof SignupSchema>

function FieldIcon({ children }: { children: React.ReactNode }) {
  return <div className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-purple-200/80">{children}</div>
}

export default function SignupPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const { showToast } = useToast()
  const form = useForm<SignupFormValues>({ resolver: zodResolver(SignupSchema), defaultValues: { email: '', password: '', confirmPassword: '', fullname: '', mobile: '' } })

  const inputClass = 'h-12 w-full rounded-xl border-white/15 bg-white/10 pl-11 pr-4 text-white placeholder:text-purple-200/60 focus:border-purple-300'

  const onSubmit = async (values: SignupFormValues) => {
    try {
      setLoading(true)
      await axiosInstance.post('/api/v1/auth/signup', { email: values.email.trim().toLowerCase(), password: values.password, fullname: values.fullname, mobile: values.mobile })
      showToast('Account created successfully!', 'success')
      router.push('/auth/login')
    } catch (error: any) {
      showToast(error?.response?.data?.detail || error?.message || 'An error occurred during signup', 'error')
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
              <h2 className="text-2xl font-bold gradient-text mb-2">Create Your Account</h2>
              <p className="text-sm text-purple-100">Join AlgoAgentX and start trading smarter</p>
            </div>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <div><label className="block text-sm font-semibold text-purple-100 mb-2">Full Name</label><div className="relative"><FieldIcon><User size={16} /></FieldIcon><Input placeholder="Your full name" className={inputClass} {...form.register('fullname')} /></div></div>
              <div><label className="block text-sm font-semibold text-purple-100 mb-2">Mobile Number</label><div className="relative"><FieldIcon><Phone size={16} /></FieldIcon><Input placeholder="+91 98765 43210" className={inputClass} {...form.register('mobile')} /></div></div>
              <div><label className="block text-sm font-semibold text-purple-100 mb-2">Email Address</label><div className="relative"><FieldIcon><Mail size={16} /></FieldIcon><Input type="email" placeholder="your@email.com" className={inputClass} {...form.register('email')} /></div>{form.formState.errors.email && <p className="mt-1 text-sm text-red-300">{form.formState.errors.email.message}</p>}</div>
              <div><label className="block text-sm font-semibold text-purple-100 mb-2">Password</label><div className="relative"><FieldIcon><Lock size={16} /></FieldIcon><Input type={showPassword ? 'text' : 'password'} placeholder="Minimum 8 characters" className={`${inputClass} pr-12`} {...form.register('password')} /><button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200 hover:text-white">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{form.formState.errors.password && <p className="mt-1 text-sm text-red-300">{form.formState.errors.password.message}</p>}</div>
              <div><label className="block text-sm font-semibold text-purple-100 mb-2">Confirm Password</label><div className="relative"><FieldIcon><Lock size={16} /></FieldIcon><Input type={showConfirmPassword ? 'text' : 'password'} placeholder="Confirm password" className={`${inputClass} pr-12`} {...form.register('confirmPassword')} /><button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-purple-200 hover:text-white">{showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{form.formState.errors.confirmPassword && <p className="mt-1 text-sm text-red-300">{form.formState.errors.confirmPassword.message}</p>}</div>
              <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-purple-500 font-semibold text-white shadow-xl">{loading ? <ThreeDots color="#FFFFFF" height={20} width={40} /> : 'Create Account'}</Button>
            </form>
            <div className="my-6 flex items-center gap-3"><div className="h-px flex-1 bg-white/15" /><span className="text-xs font-bold uppercase tracking-[0.25em] text-purple-200">or continue with</span><div className="h-px flex-1 bg-white/15" /></div>
            <GoogleAuthButton rememberMe={true} />
            <div className="mt-7 text-center text-sm text-purple-100">Already have an account? <a href="/auth/login" className="font-semibold text-purple-200 hover:text-white">Sign in</a></div>
          </div>
        </div>
      </div>
    </AuthShell>
  )
}
