'use client'

import { GlassCard } from '@/components/ui/GlassCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Manage preferences, security, and integrations."
      />
      <div className="grid gap-6 md:grid-cols-2">
        <GlassCard>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Security</h3>
            <div className="space-y-2">
              <Label>Change Password</Label>
              <Input type="password" placeholder="New password" />
            </div>
            <div className="space-y-2">
              <Label>Confirm Password</Label>
              <Input type="password" placeholder="Confirm new password" />
            </div>
            <Button className="w-full">Update Password</Button>
            <p className="text-sm text-white/60">
              (Hook this button to your existing change-password API.)
            </p>
          </div>
        </GlassCard>

        <GlassCard>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Preferences</h3>
            <div className="space-y-2">
              <Label>Default Broker</Label>
              <Input placeholder="e.g., Upstox" />
            </div>
            <div className="space-y-2">
              <Label>Default Strategy</Label>
              <Input placeholder="e.g., Swing-ML-V1" />
            </div>
            <Button className="w-full" variant="outline">Save Preferences</Button>
            <p className="text-sm text-white/60">
              (Connect this to your profile/config endpoints.)
            </p>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
