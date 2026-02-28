import type { Config } from "tailwindcss";
import { colors, spacing, borderRadius, shadows, typography, transitions, zIndex } from "./components/ui/design-tokens";

const config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: typography.fontFamily.sans,
        mono: typography.fontFamily.mono,
      },
      
      colors: {
        // CSS Variable-based Colors
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--bg))",
        foreground: "hsl(var(--text))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--danger))",
          foreground: "hsl(var(--danger-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--surface))",
          foreground: "hsl(var(--text))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        neutral: {
          0: "hsl(var(--neutral-0))",
          5: "hsl(var(--neutral-5))",
          10: "hsl(var(--neutral-10))",
          25: "hsl(var(--neutral-25))",
          50: "hsl(var(--neutral-50))",
          100: "hsl(var(--neutral-100))",
          200: "hsl(var(--neutral-200))",
          300: "hsl(var(--neutral-300))",
          400: "hsl(var(--neutral-400))",
          500: "hsl(var(--neutral-500))",
          600: "hsl(var(--neutral-600))",
          700: "hsl(var(--neutral-700))",
          800: "hsl(var(--neutral-800))",
          900: "hsl(var(--neutral-900))",
        },
      },
      
      spacing: {
        1: spacing[1],
        2: spacing[2],
        3: spacing[3],
        4: spacing[4],
        5: spacing[5],
        6: spacing[6],
        8: spacing[8],
        10: spacing[10],
        12: spacing[12],
        16: spacing[16],
        20: spacing[20],
        24: spacing[24],
        32: spacing[32],
        40: spacing[40],
        48: spacing[48],
        64: spacing[64],
      },

      borderRadius: {
        sm: borderRadius.sm,
        md: borderRadius.md,
        lg: borderRadius.lg,
        xl: borderRadius.xl,
        '2xl': borderRadius['2xl'],
        '3xl': borderRadius['3xl'],
        full: borderRadius.full,
        // Legacy compatibility (commented out to avoid conflicts)
        // lg: "var(--radius)",
        // md: "calc(var(--radius) - 2px)",
        // sm: "calc(var(--radius) - 4px)",
      },

      boxShadow: {
        sm: shadows.sm,
        md: shadows.md,
        lg: shadows.lg,
        xl: shadows.xl,
        '2xl': shadows['2xl'],
        inner: shadows.inner,
        none: shadows.none,
      },

      fontSize: {
        xs: ['12px', { lineHeight: '16px' }],
        sm: ['14px', { lineHeight: '20px' }],
        base: ['16px', { lineHeight: '24px' }],
        lg: ['18px', { lineHeight: '28px' }],
        xl: ['20px', { lineHeight: '28px' }],
        '2xl': ['24px', { lineHeight: '32px' }],
        '3xl': ['30px', { lineHeight: '36px' }],
        '4xl': ['36px', { lineHeight: '40px' }],
        '5xl': ['48px', { lineHeight: '1' }],
        '6xl': ['60px', { lineHeight: '1' }],
        '7xl': ['72px', { lineHeight: '1' }],
        '8xl': ['96px', { lineHeight: '1' }],
        '9xl': ['128px', { lineHeight: '1' }],
      },

      fontWeight: {
        light: typography.fontWeight.light,
        normal: typography.fontWeight.normal,
        medium: typography.fontWeight.medium,
        semibold: typography.fontWeight.semibold,
        bold: typography.fontWeight.bold,
        extrabold: typography.fontWeight.extrabold,
        black: typography.fontWeight.black,
      },

      letterSpacing: {
        tighter: typography.letterSpacing.tighter,
        tight: typography.letterSpacing.tight,
        normal: typography.letterSpacing.normal,
        wide: typography.letterSpacing.wide,
        wider: typography.letterSpacing.wider,
        widest: typography.letterSpacing.widest,
      },

      zIndex: {
        auto: zIndex.auto,
        base: zIndex.base,
        docked: zIndex.docked,
        dropdown: zIndex.dropdown,
        sticky: zIndex.sticky,
        banner: zIndex.banner,
        overlay: zIndex.overlay,
        modal: zIndex.modal,
        popover: zIndex.popover,
        skipLink: zIndex.skipLink,
        toast: zIndex.toast,
        tooltip: zIndex.tooltip,
      },

      transitionDuration: {
        75: transitions.duration[75],
        100: transitions.duration[100],
        150: transitions.duration[150],
        200: transitions.duration[200],
        300: transitions.duration[300],
        500: transitions.duration[500],
        700: transitions.duration[700],
        1000: transitions.duration[1000],
      },

      transitionTimingFunction: {
        linear: transitions.ease.linear,
        in: transitions.ease.in,
        out: transitions.ease.out,
        'in-out': transitions.ease['in-out'],
      },

      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        // Marquee animation for promo ticker - smooth seamless loop
        "marquee": {
          "0%": { transform: "translate3d(0, 0, 0)" },
          "100%": { transform: "translate3d(-50%, 0, 0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        // Promo ticker marquee animation - slower and smoother
        "marquee": "marquee 40s linear infinite",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/forms"),
    require("tailwind-scrollbar"),
    require("tailwindcss-debug-screens"),
  ],
} satisfies Config;

export default config;
