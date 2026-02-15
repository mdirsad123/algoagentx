"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useAtom } from "jotai";
import Cookies from "js-cookie";

import { atomCurrentUser } from "@/stores";
import { OtpSchema } from "@/schemas/auth-schema";
import { usePoster } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";

import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";

import { REGEXP_ONLY_DIGITS } from "input-otp";
import { ArrowLeft, Shield } from "lucide-react";
import { maskEmail } from "@/lib/utils";

type FormInputs = z.infer<typeof OtpSchema>;

const OTPForm = () => {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useAtom(atomCurrentUser);
  const [loading, setLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30);
  const [isLinkEnabled, setIsLinkEnabled] = useState(false);

  const form = useForm<FormInputs>({
    resolver: zodResolver(OtpSchema),
    defaultValues: { email: currentUser?.email, otp: "" },
  });

  // =================== SUCCESS HANDLER ===================
  const onSuccess = async (response: any) => {
    try {
      const { user, accessToken, refreshToken } = response;

      localStorage.setItem("access_token", accessToken);
      if (refreshToken) localStorage.setItem("refresh_token", refreshToken);

      Cookies.set("loggedinuserroleid", user.role_id, { expires: 7 });
      setCurrentUser(user);

      if (!user.is_pass_changed) {
        router.push("/changepassword");
        return;
      }

      // TEMPORARILY DISABLE ROLE-BASED REDIRECTS - Redirect to single dashboard
      router.push("/dashboard");
    } catch (error) {
      console.log(error);
    } finally {
      setLoading(false);
    }
  };

  const onError = ({ response }: any) => {
    setLoading(false);
    Toast.fire({
      icon: "error",
      title: response?.statusText,
      text: response?.data?.message,
    });
  };

  const auth = usePoster("/auth/verify-otp", "verifyotp", onSuccess, onError);

  // =================== RESEND OTP ===================
  const onResendSuccess = async (response: any) => {
    setTimeLeft(30);
    setIsLinkEnabled(false);
    Toast.fire({ icon: "success", title: "OTP", text: response.message });
  };

  const onResendError = ({ response }: any) => {
    Toast.fire({
      icon: "error",
      title: response?.statusText,
      text: response?.data?.message,
    });
  };

  const resendOtp = usePoster(
    "/auth/resend-otp",
    "resendotp",
    onResendSuccess,
    onResendError
  );

  const handleResendOTP = () => {
    resendOtp.mutate({ email: currentUser.email });
  };

  const onSubmit = (values: FormInputs) => {
    setLoading(true);
    auth.mutate(values);
  };

  // =================== TIMER ===================
  useEffect(() => {
    if (timeLeft === 0) {
      setIsLinkEnabled(true);
      return;
    }
    const timer = setInterval(() => setTimeLeft((prev) => prev - 1), 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  // =======================================================
  //                 NEW UI (Matches Login Page)
  // =======================================================

return (
  <div
    className="h-screen w-full bg-cover bg-center relative flex items-center justify-start"
    style={{
      backgroundImage: "url('/truckbg.jpg')",
      backgroundPosition: "100% 55%",
      backgroundSize: "100%",
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

    {/* Right Side OTP Card */}
    <div className="w-full flex justify-end items-center pr-28">
      <div className="w-full max-w-xl bg-white rounded-3xl shadow-2xl p-14">

        <h1 className="text-xl font-semibold text-gray-800 mb-4 text-center">
          OTP Verification
        </h1>

        <p className="text-gray-500 text-sm mb-8 text-center">
          We’ve sent a 4-digit code to {maskEmail(currentUser?.email!)}
        </p>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">

            {/* OTP Input */}
            <div className="flex justify-center">
              <FormField
                control={form.control}
                name="otp"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <InputOTP
                        {...field}
                        maxLength={4}
                        pattern={REGEXP_ONLY_DIGITS}
                        className="scale-125 dark:text-white"
                      >
                        <InputOTPGroup>
                          <InputOTPSlot index={0} />
                          <InputOTPSlot index={1} />
                          <InputOTPSlot index={2} />
                          <InputOTPSlot index={3} />
                        </InputOTPGroup>
                      </InputOTP>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Verify Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-orange-500 hover:bg-orange-600 
              text-white rounded-full text-sm font-medium transition duration-300 disabled:opacity-50"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Verifying...
                </div>
              ) : (
                <div className="flex justify-center items-center gap-2">
                  <Shield className="w-5 h-5" /> Verify Account
                </div>
              )}
            </button>

            {/* Timer / Resend */}
            <div className="text-center text-sm text-gray-600">
              {isLinkEnabled ? (
                <button
                  type="button"
                  disabled={resendOtp.isLoading}
                  onClick={handleResendOTP}
                  className="text-blue-600 hover:underline font-medium"
                >
                  {resendOtp.isLoading ? "Sending..." : "Resend OTP"}
                </button>
              ) : (
                <p>
                  You can resend OTP in{" "}
                  <span className="text-blue-700 font-bold">{timeLeft}</span> sec
                </p>
              )}
            </div>

            {/* Back Button */}
            <div className="text-center">
              <button
                type="button"
                onClick={() => router.push("/auth")}
                className="text-sm font-bold text-purple-700 hover:text-purple-800 inline-flex items-center cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Back to Login
              </button>
            </div>

          </form>
        </Form>

      </div>
    </div>

  </div>
);

};

export default OTPForm;

