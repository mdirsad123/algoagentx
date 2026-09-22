import axiosInstance from '@/lib/axios'

export type AuthSessionUser = {
  id?: string
  email?: string
  role?: string
  fullname?: string | null
  full_name?: string | null
  name?: string | null
  avatar_url?: string | null
  auth_provider?: string | null
  email_verified?: boolean
  last_login_at?: string | null
  last_login_provider?: string | null
}

const AUTH_COOKIE_NAMES = [
  'accessToken',
  'loggedinuserid',
  'loggedinusername',
  'loggedinuseremail',
  'loggedinuserfullname',
  'loggedinuserrole',
  'loggedinuserroleid',
  'loggedinuseravatar',
  'loggedinuserprovider',
]

const ONE_DAY_SECONDS = 60 * 60 * 24
const REMEMBER_ME_SECONDS = 60 * 60 * 24 * 30

type AuthSessionOptions = {
  rememberMe?: boolean
}

function getCookieMaxAge(options?: AuthSessionOptions) {
  return options?.rememberMe ? REMEMBER_ME_SECONDS : ONE_DAY_SECONDS
}

function setCookie(name: string, value: string, maxAge = ONE_DAY_SECONDS) {
  if (typeof document === 'undefined') return
  document.cookie = `${name}=${encodeURIComponent(value || '')}; path=/; max-age=${maxAge}; samesite=strict`
}

export function setAuthSession(accessToken: string, user: AuthSessionUser, options: AuthSessionOptions = {}) {
  if (typeof window === 'undefined') return

  const normalizedUser: AuthSessionUser = {
    ...user,
    email: (user.email || '').trim().toLowerCase(),
    role: user.role || 'user',
    fullname: user.fullname || user.full_name || user.name || '',
    full_name: user.full_name || user.fullname || user.name || '',
    auth_provider: user.auth_provider || 'local',
  }

  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('currentUser', JSON.stringify(normalizedUser))
  localStorage.setItem('rememberMe', options.rememberMe ? 'true' : 'false')
  axiosInstance.defaults.headers['Authorization'] = `Bearer ${accessToken}`

  const maxAge = getCookieMaxAge(options)
  setCookie('accessToken', accessToken, maxAge)
  setCookie('loggedinuserid', normalizedUser.id || '', maxAge)
  setCookie('loggedinusername', normalizedUser.email || '', maxAge)
  setCookie('loggedinuseremail', normalizedUser.email || '', maxAge)
  setCookie('loggedinuserfullname', normalizedUser.full_name || normalizedUser.fullname || '', maxAge)
  setCookie('loggedinuserrole', normalizedUser.role || 'user', maxAge)
  setCookie('loggedinuserroleid', normalizedUser.role || 'user', maxAge)
  setCookie('loggedinuseravatar', normalizedUser.avatar_url || '', maxAge)
  setCookie('loggedinuserprovider', normalizedUser.auth_provider || 'local', maxAge)
}

export function clearAuthSession() {
  if (typeof window === 'undefined') return

  localStorage.removeItem('access_token')
  localStorage.removeItem('currentUser')
  localStorage.removeItem('rememberMe')
  delete axiosInstance.defaults.headers['Authorization']

  AUTH_COOKIE_NAMES.forEach((name) => {
    document.cookie = `${name}=; path=/; max-age=0; samesite=strict`
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict`
  })
}

export function getProviderLabel(provider?: string | null, lastLoginProvider?: string | null) {
  const value = String(lastLoginProvider || provider || 'local').toLowerCase()
  return value === 'google' ? 'Google Account' : 'Local Account'
}
