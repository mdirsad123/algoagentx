"use client";

import React, { useState } from 'react';
import { Mail, ArrowLeft, Send, TrendingUp, Users, MapPin, BarChart3, ShieldCheck, MailCheck, KeyRound, Smile, Shield } from 'lucide-react';
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { usePoster } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { Input } from "@/components/ui/input";
import { maskEmail } from "@/lib/utils";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useRouter } from "next/navigation";

// Forgot Password Schema
const ForgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Please enter a valid email address"),
});

type FormInputs = z.infer<typeof ForgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const form = useForm<FormInputs>({
    resolver: zodResolver(ForgotPasswordSchema),
    defaultValues: {
      email: '',
    },
  });

  const onSuccess = (response: any) => {
    console.log("got password change response", response);

    Toast.fire({
      icon: "success",
      title: `Password sent successfully to ${maskEmail(response.email)}`,
    });

    form.reset();
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e.response?.data?.message || "Failed to Send password",
    });
  };

  const forgotPassword = usePoster(`/auth/forgot-password`, "ForgotPassword", onSuccess, onError);

  const onSubmit = (values: FormInputs) => {
    const data = values;
    try {
      forgotPassword.mutate(data);
      console.log("got change password values", data);
    } catch (error) {
      console.log(error);
      console.log("got change password values", values);
    }
  };

return (
<div
  className="h-screen w-full bg-cover bg-center relative flex items-center justify-start"
  style={{
    backgroundImage: "url('/truckbg.jpg')",
    backgroundPosition: "100% 55%", // pushes image further to the RIGHT
    backgroundSize: "100%", // zoomed in
  }}
>

    {/* Logo on left top */}
    <div className="absolute top-6 left-6 flex items-center gap-3">
      <img
        src="/product.svg"
        alt="Fleet Logo"
        className="w-50 h-auto object-contain"
      />
    </div>

    {/* Right Side Form Card */}
    <div className="w-full flex justify-end items-center pr-28">
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-2xl p-14">
        
        <h1 className="text-xl font-semibold text-gray-800 mb-4 text-center">
          Forgot Password
        </h1>

        <p className="text-gray-500 text-sm mb-8">Enter your email address to receive a password reset link</p>

        <Form {...form}>
          <div className="space-y-6">

            {/* Email Field */}
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm text-gray-800">
                    Email address <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      placeholder="mango.green@test.com"
                      className="w-full h-11 border border-gray-300 rounded-md focus:ring-2 focus:ring-orange-400"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Button */}
            <button
              type="button"
              onClick={form.handleSubmit(onSubmit)}
              disabled={forgotPassword.isLoading}
              className="w-full h-11 bg-orange-500 text-white rounded-full text-sm font-medium hover:bg-orange-600 transition disabled:opacity-50"
            >
              {forgotPassword.isLoading ? "Sending..." : "Continue"}
            </button>

            {/* Login Link */}
            <div className="text-center">
                <button
                  type="button"
                  onClick={() => router.push("/auth")}
                  className="text-sm font-bold text-purple-700 transition-colors cursor-pointer inline-flex items-center hover:text-purple-800"
                >
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  Back to Login
                </button>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                <h4 className="text-sm font-semibold text-gray-800 mb-2">Need Help?</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>• Check your spam/junk folder if you don&apos;t see the email</li>
                  <li>• After login, please reset your password</li>
                  <li>• Contact support if you continue having issues</li>
                </ul>
              </div>


          </div>
        </Form>

      </div>
    </div>
  </div>
);


}