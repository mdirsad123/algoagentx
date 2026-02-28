// Design Tokens for AlgoAgentX
// This file contains all design tokens used throughout the application

export const colors = {
  // Modern SaaS Primary Brand Colors
  primary: {
    50: '#f0f7ff',
    100: '#e0efff',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  },
  
  // Semantic Colors
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },
  
  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },
  
  danger: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },
  
  info: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },

  // Modern SaaS Neutral Scale
  neutral: {
    0: '#ffffff',
    5: '#f8fafc',
    10: '#f1f5f9',
    25: '#e2e8f0',
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
  },

  // Dark Mode Specific Colors (Professional dark theme)
  dark: {
    background: '#0b1220',        // Very dark gray, not pure black
    surface: '#111827',           // Slightly lighter than background for cards
    'surface-2': '#1f2937',       // Even lighter for elevated surfaces
    border: '#374151',            // Subtle but visible borders
    'text-primary': '#f9fafb',    // Near-white, not pure white
    'text-secondary': '#d1d5db',  // Light gray for secondary text
    'text-muted': '#9ca3af',      // Muted text
    accent: '#1f2937',            // Dark accent color
  },

  // Functional Colors
  border: '#e5e7eb',
  background: '#ffffff',
  foreground: '#0f172a',
  muted: '#64748b',
  accent: '#f8fafc',
  ring: '#2563eb',
  input: '#e5e7eb',
};

export const spacing = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
  32: '128px',
  40: '160px',
  48: '192px',
  64: '256px',
};

export const borderRadius = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '20px',
  '3xl': '24px',
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
  none: 'none',
};

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
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
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
    black: '900',
  },

  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
};

export const transitions = {
  duration: {
    75: '75ms',
    100: '100ms',
    150: '150ms',
    200: '200ms',
    300: '300ms',
    500: '500ms',
    700: '700ms',
    1000: '1000ms',
  },

  ease: {
    linear: 'linear',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

export const zIndex = {
  auto: 'auto',
  base: '0',
  docked: '10',
  dropdown: '1000',
  sticky: '1100',
  banner: '1200',
  overlay: '1300',
  modal: '1400',
  popover: '1500',
  skipLink: '1600',
  toast: '1700',
  tooltip: '1800',
};

// Utility functions for generating CSS-in-JS styles
export const getSpacing = (value: keyof typeof spacing) => spacing[value];
export const getBorderRadius = (value: keyof typeof borderRadius) => borderRadius[value];
export const getShadow = (value: keyof typeof shadows) => shadows[value];
export const getColor = (color: keyof typeof colors, shade: keyof typeof colors[keyof typeof colors]) => colors[color][shade];

// CSS Custom Properties for Tailwind integration
export const cssCustomProperties = {
  '--primary-50': colors.primary[50],
  '--primary-100': colors.primary[100],
  '--primary-200': colors.primary[200],
  '--primary-300': colors.primary[300],
  '--primary-400': colors.primary[400],
  '--primary-500': colors.primary[500],
  '--primary-600': colors.primary[600],
  '--primary-700': colors.primary[700],
  '--primary-800': colors.primary[800],
  '--primary-900': colors.primary[900],

  '--success-50': colors.success[50],
  '--success-100': colors.success[100],
  '--success-200': colors.success[200],
  '--success-300': colors.success[300],
  '--success-400': colors.success[400],
  '--success-500': colors.success[500],
  '--success-600': colors.success[600],
  '--success-700': colors.success[700],
  '--success-800': colors.success[800],
  '--success-900': colors.success[900],

  '--warning-50': colors.warning[50],
  '--warning-100': colors.warning[100],
  '--warning-200': colors.warning[200],
  '--warning-300': colors.warning[300],
  '--warning-400': colors.warning[400],
  '--warning-500': colors.warning[500],
  '--warning-600': colors.warning[600],
  '--warning-700': colors.warning[700],
  '--warning-800': colors.warning[800],
  '--warning-900': colors.warning[900],

  '--danger-50': colors.danger[50],
  '--danger-100': colors.danger[100],
  '--danger-200': colors.danger[200],
  '--danger-300': colors.danger[300],
  '--danger-400': colors.danger[400],
  '--danger-500': colors.danger[500],
  '--danger-600': colors.danger[600],
  '--danger-700': colors.danger[700],
  '--danger-800': colors.danger[800],
  '--danger-900': colors.danger[900],

  '--neutral-0': colors.neutral[0],
  '--neutral-5': colors.neutral[5],
  '--neutral-10': colors.neutral[10],
  '--neutral-25': colors.neutral[25],
  '--neutral-50': colors.neutral[50],
  '--neutral-100': colors.neutral[100],
  '--neutral-200': colors.neutral[200],
  '--neutral-300': colors.neutral[300],
  '--neutral-400': colors.neutral[400],
  '--neutral-500': colors.neutral[500],
  '--neutral-600': colors.neutral[600],
  '--neutral-700': colors.neutral[700],
  '--neutral-800': colors.neutral[800],
  '--neutral-900': colors.neutral[900],

  '--border': colors.border,
  '--background': colors.background,
  '--foreground': colors.foreground,
  '--muted': colors.muted,
  '--accent': colors.accent,
  '--ring': colors.ring,
  '--input': colors.input,
};