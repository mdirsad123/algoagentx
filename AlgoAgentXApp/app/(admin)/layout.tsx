import AppShell from '@/components/layout/AppShell'
import AuthGate from '@/components/guards/AuthGate'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate requireAdmin>
      <AppShell>{children}</AppShell>
    </AuthGate>
  )
}
