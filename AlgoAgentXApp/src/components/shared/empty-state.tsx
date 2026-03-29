import React from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Play, Plus, Search, Calendar, TrendingUp, TrendingDown, Clock, Eye, Download, AlertCircle, CheckCircle, X } from 'lucide-react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: React.ReactNode
  actionLabel?: string
  onAction?: () => void
  actionHref?: string
  secondaryActionLabel?: string
  secondaryActionHref?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  actionHref,
  secondaryActionLabel,
  secondaryActionHref,
  variant = 'default'
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return {
          bg: 'bg-green-50 dark:bg-green-900/20',
          text: 'text-green-600 dark:text-green-400',
          icon: <CheckCircle className="w-12 h-12 text-green-500" />,
          border: 'border-green-200 dark:border-green-800'
        }
      case 'warning':
        return {
          bg: 'bg-yellow-50 dark:bg-yellow-900/20',
          text: 'text-yellow-600 dark:text-yellow-400',
          icon: <Clock className="w-12 h-12 text-yellow-500" />,
          border: 'border-yellow-200 dark:border-yellow-800'
        }
      case 'error':
        return {
          bg: 'bg-red-50 dark:bg-red-900/20',
          text: 'text-red-600 dark:text-red-400',
          icon: <AlertCircle className="w-12 h-12 text-red-500" />,
          border: 'border-red-200 dark:border-red-800'
        }
      default:
        return {
          bg: 'bg-gray-50 dark:bg-gray-800',
          text: 'text-gray-600 dark:text-gray-300',
          icon: <Eye className="w-12 h-12 text-gray-400" />,
          border: 'border-gray-200 dark:border-gray-700'
        }
    }
  }

  const styles = getVariantStyles()

  const handleAction = () => {
    if (actionHref) {
      window.location.href = actionHref
    } else if (onAction) {
      onAction()
    }
  }

  const handleSecondaryAction = () => {
    if (secondaryActionHref) {
      window.location.href = secondaryActionHref
    }
  }

  return (
    <div className={`text-center py-12 px-6 rounded-xl border-2 ${styles.bg} ${styles.border}`}>
      <div className="mb-6 flex justify-center">
        {icon || styles.icon}
      </div>
      
      <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
      
      {description && (
        <p className={`text-lg mb-8 max-w-md mx-auto ${styles.text}`}>
          {description}
        </p>
      )}
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        {actionLabel && (
          <Button 
            onClick={handleAction}
            className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white px-8 py-3 text-sm font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:-translate-y-1"
          >
            {actionLabel}
          </Button>
        )}
        
        {secondaryActionLabel && (
          <Button 
            variant="outline"
            onClick={handleSecondaryAction}
            className="border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 px-8 py-3 text-sm font-medium transition-all duration-200"
          >
            {secondaryActionLabel}
          </Button>
        )}
      </div>
    </div>
  )
}

export default EmptyState