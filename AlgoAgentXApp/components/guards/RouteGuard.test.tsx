import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import RouteGuard from "./RouteGuard"
import { UserContext } from "@/contexts/user-context"
import { toast } from "sonner"
import { useRouter, usePathname } from "next/navigation"

// Mock dependencies
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
}))

jest.mock("sonner", () => ({
  toast: {
    error: jest.fn(),
  },
}))

jest.mock("@/lib/route", () => ({
  withLocale: jest.fn((pathname: string, href: string) => `${pathname}${href}`),
}))

const mockUserContext: any = {
  user: null,
  isLoading: false,
  error: null,
  fetchUser: jest.fn(),
  clearUser: jest.fn(),
}

const MockUserProvider = ({ children, value = mockUserContext }: any) => (
  <UserContext.Provider value={value}>{children}</UserContext.Provider>
)

describe("RouteGuard", () => {
  const mockRouter = { replace: jest.fn() }

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue(mockRouter)
  })

  it("renders children when requireAuth is false", () => {
    ;(usePathname as jest.Mock).mockReturnValue("/en")

    render(
      <MockUserProvider>
        <RouteGuard requireAuth={false}>
          <div>Protected Content</div>
        </RouteGuard>
      </MockUserProvider>
    )

    expect(screen.getByText("Protected Content")).toBeInTheDocument()
  })

  it("shows loading state when isLoading is true", () => {
    ;(usePathname as jest.Mock).mockReturnValue("/en")

    render(
      <MockUserProvider value={{ ...mockUserContext, isLoading: true }}>
        <RouteGuard requireAuth>
          <div>Protected Content</div>
        </RouteGuard>
      </MockUserProvider>
    )

    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument()
  })

  it("redirects to login when requireAuth is true and user is null", async () => {
    ;(usePathname as jest.Mock).mockReturnValue("/en/dashboard")

    render(
      <MockUserProvider>
        <RouteGuard requireAuth>
          <div>Protected Content</div>
        </RouteGuard>
      </MockUserProvider>
    )

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledWith("/en/dashboard/auth/login")
    })
  })

  it("redirects to dashboard and shows toast when requireAdmin is true and user is not admin", async () => {
    ;(usePathname as jest.Mock).mockReturnValue("/en/admin/dashboard")

    const userContext = {
      ...mockUserContext,
      user: { id: "1", email: "user@test.com", role: "user" },
      isLoading: false,
    }

    render(
      <MockUserProvider value={userContext}>
        <RouteGuard requireAuth requireAdmin>
          <div>Admin Content</div>
        </RouteGuard>
      </MockUserProvider>
    )

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Not authorized", {
        description: "You need admin privileges to access this page.",
      })
      expect(mockRouter.replace).toHaveBeenCalledWith(
        "/en/admin/dashboard/dashboard"
      )
    })
  })

  it("renders children when user is authenticated and admin", () => {
    ;(usePathname as jest.Mock).mockReturnValue("/en/admin/dashboard")

    const userContext = {
      ...mockUserContext,
      user: { id: "1", email: "admin@test.com", role: "admin" },
      isLoading: false,
    }

    render(
      <MockUserProvider value={userContext}>
        <RouteGuard requireAuth requireAdmin>
          <div>Admin Content</div>
        </RouteGuard>
      </MockUserProvider>
    )

    expect(screen.getByText("Admin Content")).toBeInTheDocument()
  })
})
