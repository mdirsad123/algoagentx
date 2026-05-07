import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = new Set([
  '/',
  '/auth/login',
  '/auth/signup',
  '/auth/admin-login',
  '/auth/forgotpassword',
  '/auth/forgot-password',
  '/auth/reset-password',
])

function isPublic(pathname: string) {
  if (PUBLIC_PATHS.has(pathname)) return true
  if (pathname.startsWith('/_next')) return true
  if (pathname.startsWith('/favicon')) return true
  if (pathname.startsWith('/public')) return true
  return false
}

function isJwtExpired(token: string) {
  try {
    const [, payload] = token.split('.')
    if (!payload) return true
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=')
    const decoded = JSON.parse(atob(padded))
    if (!decoded?.exp) return false
    return decoded.exp * 1000 <= Date.now()
  } catch {
    return true
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  if (isPublic(pathname)) return NextResponse.next()

  const protectedPrefixes = [
    '/dashboard', '/brokers', '/strategies', '/backtest', '/backtest-history',
    '/reports', '/pricing', '/credits', '/profile', '/myprofile', '/settings',
    '/live-trading', '/live-approval', '/admin'
  ]
  const needsAuth = protectedPrefixes.some(p => pathname === p || pathname.startsWith(p + '/'))
  if (!needsAuth) return NextResponse.next()

  const token = request.cookies.get('accessToken')?.value
  if (!token || isJwtExpired(token)) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = pathname.startsWith('/admin') ? '/auth/admin-login' : '/auth/login'
    loginUrl.searchParams.set('redirect', pathname)
    const response = NextResponse.redirect(loginUrl)
    response.cookies.delete('accessToken')
    response.cookies.delete('loggedinuserroleid')
    return response
  }

  const role = request.cookies.get('loggedinuserroleid')?.value || request.cookies.get('loggedinuserrole')?.value || ''
  const isAdmin = role === 'admin' || role === '1'

  if (pathname.startsWith('/admin') && !isAdmin) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // Keep admin users on admin workspace by default if they accidentally open user dashboard routes.
  if (isAdmin && !pathname.startsWith('/admin') && pathname !== '/auth/admin-login') {
    const userOnlyPrefixes = ['/dashboard', '/backtest', '/live-trading', '/profile', '/myprofile']
    if (userOnlyPrefixes.some(p => pathname === p || pathname.startsWith(p + '/'))) {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/dashboard'
      return NextResponse.redirect(url)
    }
  }

  return NextResponse.next()
}

export const config = { matcher: ['/((?!api).*)'] }
