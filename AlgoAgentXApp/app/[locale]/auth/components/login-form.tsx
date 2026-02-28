import { AuthSchema } from "@/schemas/auth-schema";
import React, { useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Brain, Eye, EyeOff } from 'lucide-react';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Input } from "@/components/ui/input";
import Toast from "@/components/shared/toast";
import Cookies from "js-cookie";
import axiosInstance from "@/lib/axios";

type FormInputs = z.infer<typeof AuthSchema>;

const LoginForm = () => {
  const router = useRouter();
  const form = useForm<FormInputs>({
    resolver: zodResolver(AuthSchema),
    defaultValues: { user_name: "", password: "" },
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const onSubmit = async (values: FormInputs) => {
    try {
      setLoading(true);

      // Call AlgoAgentX API login endpoint
      const response = await axiosInstance.post('/api/v1/auth/login', {
        email: values.user_name, // Map user_name to email for our API
        password: values.password
      });

      const { access_token, user } = response.data;

      // Store token
      localStorage.setItem("access_token", access_token);

      // Set cookies
      Cookies.set("accessToken", access_token, { expires: 7 });
      Cookies.set("loggedinuserroleid", user.role, { expires: 7 });
      Cookies.set("loggedinuserid", user.id, { expires: 7 });
      Cookies.set("loggedinusername", user.email, { expires: 7 });
      Cookies.set("loggedinuseremail", user.email, { expires: 7 });

      // Set authorization header for future requests
      axiosInstance.defaults.headers["Authorization"] = `Bearer ${access_token}`;

      Toast.fire({
        icon: 'success',
        title: 'Login successful!',
        text: 'Welcome to AlgoAgentX'
      });

      // Redirect based on user role
      if (user.role === 'admin') {
        router.push("/admin/dashboard");
      } else {
        router.push("/dashboard");
      }

    } catch (error: any) {
      console.error('Login error:', error);
      Toast.fire({
        icon: 'error',
        title: 'Login failed',
        text: error.response?.data?.detail || 'An error occurred during login'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">

      {/* Centered Form Card */}
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-slate-200 p-8">

        {/* Header with AlgoAgentX branding */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-slate-900 rounded-lg">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div className="text-2xl font-bold text-slate-900">AlgoAgentX</div>
          </div>
          <h1 className="text-xl font-semibold text-slate-800 mb-2">
            Welcome Back
          </h1>
          <p className="text-slate-600 text-sm">
            Sign in to access your trading dashboard
          </p>
        </div>

        <Form {...form}>
          <div className="space-y-6">

            {/* Email */}
            <FormField
              control={form.control}
              name="user_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">
                    Email address <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      maxLength={60}
                      placeholder="Enter your email"
                      className="w-full h-11 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-colors"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Password */}
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-slate-700">
                    Password <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        {...field}
                        type={showPassword ? "text" : "password"}
                        maxLength={15}
                        placeholder="Enter your password"
                        className="w-full h-11 border border-slate-300 rounded-lg pr-12 focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Login Button */}
            <button
              type="button"
              onClick={form.handleSubmit(onSubmit)}
              disabled={loading}
              className="w-full h-11 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Continue"}
            </button>

            {/* Divider */}
            <div className="text-center text-sm text-slate-500">
              Don't have an account?
            </div>

            {/* Create Account */}
            <button
              type="button"
              onClick={() => router.push("/auth/signup")}
              className="w-full h-11 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Create an account
            </button>
          </div>
        </Form>

      </div>

    </div>
  );
};

export default LoginForm;
