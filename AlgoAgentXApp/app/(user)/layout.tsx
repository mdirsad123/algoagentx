import Sidebar from '@/components/layout/Sidebar'
import Topbar from '@/components/layout/Topbar'
import AuthGate from '@/components/guards/AuthGate'
import CouponAnnouncementBar from '@/components/common/CouponAnnouncementBar'

export default function UserLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <div className="min-h-screen bg-gradient-to-br from-[#120826] via-[#4a178f] to-[#1a2448]">
        <Sidebar />
        <div className="ml-[88px] flex min-h-screen flex-1 flex-col xl:ml-64">
          <CouponAnnouncementBar />
          <Topbar />
          <main className="flex-1 px-4 py-6 md:px-6">{children}</main>
        </div>
      </div>
    </AuthGate>
  )
}
