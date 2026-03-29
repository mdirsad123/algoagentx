'use client'

import React from 'react'
import { UserProvider } from '@/contexts/user-context'

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <UserProvider>
      {children}
    </UserProvider>
  )
}
