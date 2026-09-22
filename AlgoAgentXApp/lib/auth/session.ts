export type AuthUser = {
  id: string
  email: string
  role: string
  fullname?: string
  full_name?: string
  avatar_url?: string
  auth_provider?: string
}

const AUTH_COOKIE_NAMES = [
  'accessToken',
  'loggedinuserid',
  'loggedinusername',
  'loggedinuseremail',
  'loggedinuserfullname',
  'loggedinuserrole',
  'loggedinuserroleid',
]

const cookieOptions = (maxAgeSeconds: number) => {
  const secure = typeof window !== 'undefined' && window.location.protocol === 'https:' ? '; secure' : ''
  return `path=/; max-age=${maxAgeSeconds}; samesite=lax${secure}`
}

const setCookie = (name: string, value: string, maxAgeSeconds: number) => {
  document.cookie = `${name}=${encodeURIComponent(value || '')}; ${cookieOptions(maxAgeSeconds)}`
}

export const getAuthMaxAgeSeconds = (rememberMe?: boolean) => rememberMe ? 60 * 60 * 24 * 30 : 60 * 60 * 24

export const setAuthSession = (token: string, user: AuthUser, options?: { rememberMe?: boolean }) => {
  if (typeof window === 'undefined') return
  const maxAge = getAuthMaxAgeSeconds(options?.rememberMe)
  const displayName = user.fullname || user.full_name || ''

  localStorage.setItem('access_token', token)
  localStorage.setItem('currentUser', JSON.stringify(user))
  localStorage.setItem('rememberMe', options?.rememberMe ? 'true' : 'false')

  setCookie('accessToken', token, maxAge)
  setCookie('loggedinuserid', user.id || '', maxAge)
  setCookie('loggedinusername', user.email || '', maxAge)
  setCookie('loggedinuseremail', user.email || '', maxAge)
  setCookie('loggedinuserfullname', displayName, maxAge)
  setCookie('loggedinuserrole', user.role || '', maxAge)
  setCookie('loggedinuserroleid', user.role || '', maxAge)
}

export const clearAuthSession = () => {
  if (typeof window === 'undefined') return
  localStorage.removeItem('access_token')
  localStorage.removeItem('currentUser')
  localStorage.removeItem('rememberMe')
  AUTH_COOKIE_NAMES.forEach((name) => {
    document.cookie = `${name}=; path=/; max-age=0; samesite=lax`
  })
}
