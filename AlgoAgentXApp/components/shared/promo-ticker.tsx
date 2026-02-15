import React, { useState, useEffect, useRef } from "react";
import { X } from "lucide-react";
import Link from "next/link";

interface PromoTickerProps {
  content?: string;
  buttonText?: string;
  buttonLink?: string;
}

export default function PromoTicker({ 
  content = "Get 30% OFF on first upgrade with code FIRST30 (new users only)", 
  buttonText = "Upgrade now", 
  buttonLink = "/pricing" 
}: PromoTickerProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [isHovered, setIsHovered] = useState(false);
  const tickerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if ticker was dismissed
    const dismissed = localStorage.getItem('promo-ticker-dismissed');
    if (dismissed === 'true') {
      setIsVisible(false);
    }
  }, []);

  useEffect(() => {
    // Handle infinite scrolling animation
    const ticker = tickerRef.current;
    const text = textRef.current;
    
    if (!ticker || !text) return;

    const tickerWidth = ticker.offsetWidth;
    const textWidth = text.scrollWidth;

    if (textWidth <= tickerWidth) return; // No need to scroll if text fits

    let animationId: number;
    let startTime: number;
    const duration = 20000; // 20 seconds for one complete cycle

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      
      // Calculate progress (0 to 1)
      const progress = (elapsed % duration) / duration;
      
      // Move text from right to left
      const translateX = tickerWidth - (progress * (textWidth + tickerWidth));
      
      text.style.transform = `translateX(${translateX}px)`;
      
      if (isVisible && !isHovered) {
        animationId = requestAnimationFrame(animate);
      }
    };

    if (isVisible && !isHovered) {
      animationId = requestAnimationFrame(animate);
    }

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [isVisible, isHovered]);

  const handleClose = () => {
    setIsVisible(false);
    localStorage.setItem('promo-ticker-dismissed', 'true');
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div 
      className="bg-gradient-to-r from-blue-600 via-blue-700 to-blue-800 text-white shadow-lg"
      ref={tickerRef}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-12">
          {/* Scrolling text container */}
          <div className="flex-1 overflow-hidden">
            <div 
              ref={textRef}
              className="whitespace-nowrap text-sm font-medium"
              style={{ 
                willChange: 'transform',
                display: 'inline-block'
              }}
            >
              {/* Duplicate text for seamless loop */}
              <span className="mr-8">{content}</span>
              <span>{content}</span>
            </div>
          </div>

          {/* Action button */}
          <div className="ml-4 flex-shrink-0">
            <Link
              href={buttonLink}
              className="bg-white text-blue-600 px-4 py-1.5 rounded-md text-sm font-semibold hover:bg-gray-100 transition-colors shadow-md"
            >
              {buttonText}
            </Link>
          </div>

          {/* Close button */}
          <button
            onClick={handleClose}
            className="ml-2 p-1 rounded-md hover:bg-white/20 transition-colors"
            aria-label="Close promo banner"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}