import { GlassCard } from '@/components/ui/GlassCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import CouponBarSettingsCard from '@/components/admin/CouponBarSettingsCard'

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Admin Settings" subtitle="Security and console preferences for the admin workspace." />
      <CouponBarSettingsCard />
      <div className="grid gap-6 md:grid-cols-2">
        <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Security</h3>
            <div className="space-y-2"><Label>Change password</Label><Input type="password" placeholder="New password" className="border-white/10 bg-white/10 text-white" /></div>
            <div className="space-y-2"><Label>Confirm password</Label><Input type="password" placeholder="Confirm password" className="border-white/10 bg-white/10 text-white" /></div>
            <Button className="w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-blue-500 text-white">Update password</Button>
          </div>
        </GlassCard>
        <GlassCard className="rounded-3xl border border-white/10 p-6 hover:scale-100">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Console preferences</h3>
            <div className="space-y-2"><Label>Default admin queue</Label><Input placeholder="Support / Billing / Strategy" className="border-white/10 bg-white/10 text-white" /></div>
            <div className="space-y-2"><Label>Escalation email</Label><Input placeholder="support@company.com" className="border-white/10 bg-white/10 text-white" /></div>
            <Button variant="outline" className="w-full rounded-xl border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">Save preferences</Button>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
