import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, RefreshCw, AlertCircle, CheckCircle, Play } from "lucide-react"
import { format } from "date-fns"
import { useState, useEffect } from "react"
import { getAiScreenerStatus, adminRunScreener } from "@/lib/api/ai-screener"
import { AiScreenerStatus } from "@/types/ai-screener"
import { toast } from "sonner"

interface StatusBarProps {
  onRefresh?: () => void
}

export function StatusBar({ onRefresh }: StatusBarProps) {
  const [status, setStatus] = useState<AiScreenerStatus | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const data = await getAiScreenerStatus()
      setStatus(data)
    } catch (error) {
      console.error("Failed to fetch AI Screener status:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Poll status every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'default'
      case 'running':
        return 'secondary'
      case 'failed':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4" />
      case 'running':
        return <Clock className="h-4 w-4" />
      case 'failed':
        return <AlertCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
    } catch {
      return 'Invalid date'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5" />
          AI Screener Status
        </CardTitle>
        <CardDescription>
          Last run times and current status for news and announcements
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* News Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">News</h4>
              <Badge variant={getStatusColor(status?.news.status || 'never_run')}>
                {getStatusIcon(status?.news.status || 'never_run')}
                <span className="ml-1">{status?.news.status || 'never_run'}</span>
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              Last run: {formatDate(status?.news?.last_run ?? null)}
            </div>
            {status?.news.error && (
              <div className="text-sm text-red-600">
                Error: {status.news.error}
              </div>
            )}
          </div>

          {/* Announcements Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Announcements</h4>
              <Badge variant={getStatusColor(status?.announcements.status || 'never_run')}>
                {getStatusIcon(status?.announcements.status || 'never_run')}
                <span className="ml-1">{status?.announcements.status || 'never_run'}</span>
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              Last run: {formatDate(status?.announcements?.last_run ?? null)}
            </div>
            {status?.announcements.error && (
              <div className="text-sm text-red-600">
                Error: {status.announcements.error}
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-between items-center pt-2">
          <div className="text-xs text-muted-foreground">
            Auto-refreshes every 30 seconds
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="text-sm text-primary hover:text-primary/80 disabled:opacity-50"
            >
              {loading ? 'Refreshing...' : 'Refresh Now'}
            </button>
            <button
              onClick={async () => {
                try {
                  await adminRunScreener('news');
                  toast.success('News refresh initiated');
                  // Refresh status after a short delay
                  setTimeout(fetchStatus, 1000);
                } catch (error) {
                  toast.error('Failed to initiate news refresh');
                }
              }}
              disabled={loading}
              className="flex items-center space-x-2 px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              <span>Run News Now</span>
            </button>
            <button
              onClick={async () => {
                try {
                  await adminRunScreener('announcements');
                  toast.success('Announcements refresh initiated');
                  // Refresh status after a short delay
                  setTimeout(fetchStatus, 1000);
                } catch (error) {
                  toast.error('Failed to initiate announcements refresh');
                }
              }}
              disabled={loading}
              className="flex items-center space-x-2 px-3 py-1 text-sm bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              <span>Run Announcements Now</span>
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
