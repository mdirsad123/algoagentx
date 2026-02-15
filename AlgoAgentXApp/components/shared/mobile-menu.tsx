'use client';

import React from 'react';
import { X } from 'lucide-react';
import SideBar from './sidebar';

interface MobileMenuProps {
  setOpen: (open: boolean) => void;
}

export default function MobileMenu({ setOpen }: MobileMenuProps) {
  const handleClose = React.useCallback(() => {
    setOpen(false);
  }, [setOpen]);

  return (
    <div className="relative h-full">
      {/* Close button */}
      <button
        onClick={handleClose}
        className="absolute top-4 right-4 z-10 p-2 rounded-md hover:bg-gray-100"
      >
        <X className="w-6 h-6" />
      </button>

      {/* Sidebar content */}
      <div className="pt-12">
        <SideBar />
      </div>
    </div>
  );
}
