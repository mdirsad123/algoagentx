"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { withLocale } from "@/lib/route";
import { Sparkles } from "lucide-react";

export default function PromoTicker() {
  const pathname = usePathname();

  // Array of promo items for clean duplication
  const promoItems = [
    {
      icon: "🎉",
      text: "Use code FIRST30 to get 30% OFF on your first upgrade",
      buttonText: "Upgrade now",
    },
    {
      icon: "🚀", 
      text: "Join 10,000+ traders using AlgoAgentX for automated trading",
      buttonText: "Get Started",
    },
    {
      icon: "💎",
      text: "Limited Time: Free AI Screener credits with Pro plans", 
      buttonText: "Learn More",
    },
  ];

  return (
    <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-2 px-4 overflow-hidden relative">
      <div className="flex animate-marquee hover:[animation-play-state:paused]">
        {/* Render items twice for seamless loop */}
        {[...promoItems, ...promoItems].map((item, index) => (
          <div key={index} className="flex items-center space-x-2 whitespace-nowrap px-8">
            <Sparkles className="w-4 h-4 shrink-0" />
            <span className="font-medium">
              {item.icon} {item.text}
            </span>
            <Link
              href={withLocale(pathname, "/pricing")}
              className="bg-white bg-opacity-20 hover:bg-opacity-30 px-3 py-1 rounded-full text-sm font-semibold transition-all duration-200 hover:scale-105 backdrop-blur-sm shrink-0"
            >
              {item.buttonText}
            </Link>
          </div>
        ))}
      </div>
      
      {/* Subtle fade edges */}
      <div className="absolute left-0 top-0 w-8 h-full bg-gradient-to-r from-blue-600 to-transparent pointer-events-none" />
      <div className="absolute right-0 top-0 w-8 h-full bg-gradient-to-l from-purple-600 to-transparent pointer-events-none" />
    </div>
  );
}
