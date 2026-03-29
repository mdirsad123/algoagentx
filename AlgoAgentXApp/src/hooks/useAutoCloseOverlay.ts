import { useEffect, useRef } from "react"
import { usePathname } from "next/navigation"

interface UseAutoCloseOverlayProps {
  open: boolean
  onClose: () => void
  containerRef: React.RefObject<HTMLElement>
  closeOnPathChange?: boolean
}

export function useAutoCloseOverlay({
  open,
  onClose,
  containerRef,
  closeOnPathChange = true
}: UseAutoCloseOverlayProps) {
  const pathname = usePathname()

  useEffect(() => {
    if (!open || !containerRef.current) return

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("keydown", handleEscapeKey)

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("keydown", handleEscapeKey)
    }
  }, [open, onClose, containerRef])

  useEffect(() => {
    if (open && closeOnPathChange) {
      onClose()
    }
  }, [pathname, open, closeOnPathChange, onClose])
}