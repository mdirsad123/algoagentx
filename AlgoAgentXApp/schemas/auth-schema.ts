import { z } from "zod";

export const AuthSchema = z.object({
  user_name: z.string().email().min(1, { message: "Email is mandatory" }),
  password: z.string().min(1,{ message: "Password is mandatory" }),
});

export const OtpSchema = z.object({
  email: z.string().email().min(1, { message: "Email is mandatory" }),
  otp: z.string().min(1,{ message: "Otp is mandatory" }),
});