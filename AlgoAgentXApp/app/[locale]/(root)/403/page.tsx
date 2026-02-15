import * as React from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ShieldAlert } from "lucide-react"
import { NotificationProvider } from "@/contexts/notification-context"

export default function ForbiddenPage() {
  const router = useRouter()

  return (
    <NotificationProvider>
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8 text-center">
          <div>
            <ShieldAlert className="mx-auto h-12 w-12 text-red-500" />
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Access Denied
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              You don't have permission to access this resource.
            </p>
          </div>
          
          <div className="mt-8 space-y-4">
            <Button
              onClick={() => router.push('/')}
              className="w-full"
            >
              Go to Dashboard
            </Button>
            
            <Button
              variant="outline"
              onClick={() => router.push('/auth/login')}
              className="w-full"
            >
              Sign In
            </Button>
          </div>
        </div>
      </div>
    </NotificationProvider>
  )
}
