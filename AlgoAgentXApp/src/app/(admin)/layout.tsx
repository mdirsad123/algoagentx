import Sidebar from '@/components/layout/Sidebar'
import Topbar from '@/components/layout/Topbar'
import AuthGate from '@/components/guards/AuthGate'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate requireAdmin>
      <div className="flex min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900">
        <Sidebar />
        <div className="flex-1 flex flex-col ml-64">
          <Topbar />
          <main className="flex-1 p-6 overflow-y-auto">
            {children}
          </main>
        </div>
      </div>
    </AuthGate>
  )
}
