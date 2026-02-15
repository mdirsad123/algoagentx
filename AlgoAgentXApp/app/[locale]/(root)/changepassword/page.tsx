"use client";

import React, { useEffect, useState } from "react";
import { Eye, EyeOff, Lock, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { cn } from "@/lib/utils";
import { useAtom } from "jotai";
import { atomCurrentUser } from "@/stores";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { usePoster } from "@/hooks/use-query";
import { useTranslation } from "@/hooks/use-translations";
import { useCurrentLocale } from "@/locales/client";

// Schema
const PasswordChangeSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z
      .string()
      .min(8, "Password must be at least 8 characters long")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/\d/, "Password must contain at least one number")
      .regex(
        /[!@#$%^&*(),.?":{}|<>]/,
        "Password must contain at least one special character"
      ),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    message: "New password must be different from current password",
    path: ["newPassword"],
  });

type FormInputs = z.infer<typeof PasswordChangeSchema>;

export default function Page() {
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [currentUser, setCurrentUser] = useAtom(atomCurrentUser);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);
  const loggedinuserid = Cookies.get("loggedinuserid");
  const loggedinuserroleid = Cookies.get("loggedinuserroleid");
  const router = useRouter();

  const locale = useCurrentLocale();

  const form = useForm<FormInputs>({
    resolver: zodResolver(PasswordChangeSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const getPasswordStrength = (password: string) => {
    let strength = 0;
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    };
    Object.values(checks).forEach((check) => check && strength++);
    return { strength, checks };
  };

  const passwordStrength = getPasswordStrength(form.watch("newPassword") || "");

  const {t, isRTL} = useTranslation();

  // TEMPORARILY DISABLE ROLE-BASED REDIRECTS
  /*
  useEffect(() => {
    if (Number(loggedinuserroleid) === 1) {
      router.replace(`/${locale}/home/dashboard_systemadmin`);
    }
  }, [loggedinuserroleid, router, locale]);
  */
  

  const getStrengthColor = (strength: number) => {
    if (strength <= 2) return "bg-red-500";
    if (strength <= 3) return "bg-yellow-500";
    if (strength <= 4) return "bg-blue-500";
    return "bg-green-500";
  };
  const getStrengthText = (strength: number) => {
    if (strength <= 2) return "Weak";
    if (strength <= 3) return "Fair";
    if (strength <= 4) return "Good";
    return "Strong";
  };
  const togglePasswordVisibility = (field: "current" | "new" | "confirm") => {
    setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const onSuccess = () => {
    form.reset();
    setShowSuccessPopup(true);
  };
  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e.response?.data?.message || "Failed to change password",
    });
  };
  const changePassword = usePoster(
    `/auth/change-password/${loggedinuserid}`,
    "changePassword",
    onSuccess,
    onError
  );

  const onSubmit = (values: FormInputs) => {
    changePassword.mutate(values);
  };

  const handleLogout = () => {
    setCurrentUser({});
    Object.keys(Cookies.get()).forEach((cookie) => Cookies.remove(cookie));
    router.push("/auth");
  };

  const goToDashboard = () => {
    // TEMPORARILY DISABLE ROLE-BASED REDIRECTS - Redirect to single dashboard
    router.push('/dashboard');
  };


  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-2 sm:p-4" dir={isRTL ? "rtl" : "ltr"}>
      {/* Success Popup */}
      {showSuccessPopup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-4 sm:p-6 max-w-sm w-full">

            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Check className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {t('auth.passwordchangedsuccess')}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-4 text-sm">
                {t('auth.passwordchangedsuccessmsg')}
              </p>
              <Button
                onClick={handleLogout}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 text-sm"
              >
                {t('auth.ok')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="w-full max-w-4xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-3 sm:p-6">
            {/* Header */}
            <div
                className={cn(
                  "flex items-center mb-4",
                  isRTL ? "flex-row-reverse space-x-3 space-x-reverse" : "flex-row space-x-3"
                )}
              >
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <Lock className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-600" />
                </div>

                <div className={cn(isRTL ? "text-right" : "text-left")}>
                  <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
                    {t("auth.changepassword")}
                  </h2>
                  <p className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
                    {t("auth.keepsecure")}
                  </p>
                </div>
              </div>

            <Form {...form}>
              <div className="space-y-4">
                {/* Current Password */}
                <FormField
                  control={form.control}
                  name="currentPassword"
                  render={({ field, fieldState }) => (
                    <FormItem>
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 sm:gap-4 items-start">
                        <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                          {t('auth.currentpassword')} <span className="text-red-500">*</span>
                        </FormLabel>
                        <div className="sm:col-span-3">
                          <div className="relative">
                            <FormControl>
                              <Input
                                type={showPasswords.current ? "text" : "password"}
                                placeholder={t('auth.entercurrentpassword')}
                                {...field}
                                className={cn(
                                  "w-full pr-10 text-sm h-9",
                                  fieldState.error &&
                                    "border-red-300 bg-red-50"
                                )}
                              />
                            </FormControl>
                            <button
                              type="button"
                              onClick={() => togglePasswordVisibility("current")}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                            >
                              {showPasswords.current ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                          <FormMessage className="text-xs mt-1" />
                        </div>
                      </div>
                    </FormItem>
                  )}
                />

                {/* New Password */}
                <FormField
                  control={form.control}
                  name="newPassword"
                  render={({ field, fieldState }) => (
                    <FormItem>
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 sm:gap-4 items-start">
                        <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                          {t('auth.newpassword')} <span className="text-red-500">*</span>
                        </FormLabel>
                        <div className="sm:col-span-3">
                          <div className="relative">
                            <FormControl>
                              <Input
                                type={showPasswords.new ? "text" : "password"}
                                placeholder={t('auth.newpassword')}
                                {...field}
                                className={cn(
                                  "w-full pr-10 text-sm h-9",
                                  fieldState.error &&
                                    "border-red-300 bg-red-50"
                                )}
                              />
                            </FormControl>
                            <button
                              type="button"
                              onClick={() => togglePasswordVisibility("new")}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                              {showPasswords.new ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          </div>

                          {/* Strength Indicator */}
                          {field.value && (
                            <div className="mt-2">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-gray-600 dark:text-gray-300">{t('auth.strength')}</span>
                                <span
                                  className={cn(
                                    "text-xs font-medium",
                                    passwordStrength.strength <= 2 &&
                                      "text-red-600",
                                    passwordStrength.strength === 3 &&
                                      "text-yellow-600",
                                    passwordStrength.strength === 4 &&
                                      "text-blue-600",
                                    passwordStrength.strength === 5 &&
                                      "text-green-600"
                                  )}
                                >
                                  {getStrengthText(passwordStrength.strength)}
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                <div
                                  className={cn(
                                    "h-1.5 rounded-full transition-all duration-300",
                                    getStrengthColor(passwordStrength.strength)
                                  )}
                                  style={{
                                    width: `${
                                      (passwordStrength.strength / 5) * 100
                                    }%`,
                                  }}
                                ></div>
                              </div>
                              <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
                                <StrengthCheck
                                  label="8+ chars"
                                  check={passwordStrength.checks.length}
                                />
                                <StrengthCheck
                                  label="A-Z"
                                  check={passwordStrength.checks.uppercase}
                                />
                                <StrengthCheck
                                  label="a-z"
                                  check={passwordStrength.checks.lowercase}
                                />
                                <StrengthCheck
                                  label="0-9"
                                  check={passwordStrength.checks.number}
                                />
                                <StrengthCheck
                                  label="!@#"
                                  check={passwordStrength.checks.special}
                                />
                              </div>
                            </div>
                          )}
                          <FormMessage className="text-xs mt-1" />
                        </div>
                      </div>
                    </FormItem>
                  )}
                />

                {/* Confirm Password */}
                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field, fieldState }) => (
                    <FormItem>
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 sm:gap-4 items-start">
                        <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                          {t('auth.confirmpassword')}{" "}
                          <span className="text-red-500">*</span>
                        </FormLabel>
                        <div className="sm:col-span-3">
                          <div className="relative">
                            <FormControl>
                              <Input
                                type={showPasswords.confirm ? "text" : "password"}
                                placeholder={t('auth.confirmnewpassword')}
                                {...field}
                                className={cn(
                                  "w-full pr-16 text-sm h-9",
                                  fieldState.error &&
                                    "border-red-300 bg-red-50",
                                  !fieldState.error &&
                                    field.value &&
                                    form.watch("newPassword") === field.value &&
                                    "border-green-300 bg-green-50"
                                )}
                              />
                            </FormControl>
                            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1">
                              {field.value &&
                                form.watch("newPassword") === field.value &&
                                !fieldState.error && (
                                  <Check className="w-4 h-4 text-green-500" />
                                )}
                              <button
                                type="button"
                                onClick={() =>
                                  togglePasswordVisibility("confirm")
                                }
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {showPasswords.confirm ? (
                                  <EyeOff className="w-4 h-4" />
                                ) : (
                                  <Eye className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                          </div>
                          <FormMessage className="text-xs mt-1" />
                        </div>
                      </div>
                    </FormItem>
                  )}
                />

                {/* Security Tips */}
                <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                <h4 className="text-xs font-medium text-blue-900 dark:text-blue-200 mb-1">
                  {t('auth.securitytips')}
                </h4>
                <div className="text-xs text-blue-800 dark:text-blue-300 grid grid-cols-1 sm:grid-cols-2 gap-1">
                    <div>{t('auth.tips1')}</div>
                    <div>{t('auth.tips2')}</div>
                    <div>{t('auth.tips3')}</div>
                    <div>{t('auth.tips4')}</div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Button
                    type="button"
                    onClick={form.handleSubmit(onSubmit)}
                    disabled={
                      changePassword.isLoading ||
                      passwordStrength.strength < 3
                    }
                    className="bg-indigo-600 hover:bg-indigo-700 text-sm h-9 flex-1"
                  >
                    {changePassword.isLoading ? (
                      <div className="flex items-center">
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                        {t('auth.updating')}
                      </div>
                    ) : (
                      t('auth.updatepassword')
                    )}
                  </Button>
                  <Button
                    onClick={goToDashboard}
                    variant="outline"
                    className="border-red-500 text-red-600 hover:bg-red-50 text-sm h-9 flex-1 sm:flex-initial"
                  >
                    {t('auth.cancel')}
                  </Button>
                </div>
              </div>
            </Form>
          </div>
        </div>
      </div>
    </div>
  );
}

function StrengthCheck({ label, check }: { label: string; check: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center text-xs",
        check ? "text-green-600" : "text-gray-400"
      )}
    >
      {check ? <Check className="w-3 h-3 mr-1" /> : <X className="w-3 h-3 mr-1" />}
      {label}
    </div>
  );
}
