import AppShell from '@/components/layout/AppShell'
import AuthGate from '@/components/guards/AuthGate'

export default function UserLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <AppShell showCouponBar>{children}</AppShell>
    </AuthGate>
  )
}
