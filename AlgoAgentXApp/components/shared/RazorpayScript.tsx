"use client";

import { useEffect } from "react";

interface RazorpayScriptProps {
  children: React.ReactNode;
}

export default function RazorpayScript({ children }: RazorpayScriptProps) {
  useEffect(() => {
    // Check if Razorpay script is already loaded
    if (typeof window !== 'undefined' && !(window as any).Razorpay) {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      document.body.appendChild(script);
    }
  }, []);

  return <>{children}</>;
}