'use client'

import React, { createContext, useContext, useState, useCallback } from 'react'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
}

interface ToastContextType {
  toasts: Toast[]
  showToast: (message: string, type?: Toast['type']) => void
  hideToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).substr(2, 9)
    setToasts(prev => [...prev, { id, message, type }])
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
      hideToast(id)
    }, 3000)
  }, [])

  const hideToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, showToast, hideToast }}>
      {children}
      <ToastContainer toasts={toasts} onHide={hideToast} />
    </ToastContext.Provider>
  )
}

interface ToastContainerProps {
  toasts: Toast[]
  onHide: (id: string) => void
}

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onHide }) => {
  const getToastStyles = (type: Toast['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-500/90 border-green-400/50 text-white'
      case 'error':
        return 'bg-red-500/90 border-red-400/50 text-white'
      case 'warning':
        return 'bg-yellow-500/90 border-yellow-400/50 text-white'
      case 'info':
      default:
        return 'bg-blue-500/90 border-blue-400/50 text-white'
    }
  }

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`glass-card ${getToastStyles(toast.type)} p-4 rounded-lg shadow-lg border backdrop-blur-sm animate-in slide-in-from-right-full duration-300`}
          role="alert"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{toast.message}</span>
            <button
              onClick={() => onHide(toast.id)}
              className="ml-4 text-white/70 hover:text-white transition-colors"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

// Simple toast component for direct use
interface ToastProps {
  message: string
  type?: 'success' | 'error' | 'warning' | 'info'
  visible: boolean
  onClose: () => void
}

export const Toast: React.FC<ToastProps> = ({ message, type = 'info', visible, onClose }) => {
  if (!visible) return null

  const getToastStyles = () => {
    switch (type) {
      case 'success':
        return 'bg-green-500/90 border-green-400/50 text-white'
      case 'error':
        return 'bg-red-500/90 border-red-400/50 text-white'
      case 'warning':
        return 'bg-yellow-500/90 border-yellow-400/50 text-white'
      case 'info':
      default:
        return 'bg-blue-500/90 border-blue-400/50 text-white'
    }
  }

  return (
    <div
      className={`fixed top-4 right-4 glass-card ${getToastStyles()} p-4 rounded-lg shadow-lg border backdrop-blur-sm animate-in slide-in-from-right-full duration-300`}
      role="alert"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{message}</span>
        <button
          onClick={onClose}
          className="ml-4 text-white/70 hover:text-white transition-colors"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export default Toast