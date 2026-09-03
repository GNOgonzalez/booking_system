import { browserTimezone } from './utils/datetime.js'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const ACCESS_KEY = 'accessToken'
const REFRESH_KEY = 'refreshToken'

/** Per-tab storage so multiple roles can stay logged in in separate Chrome tabs. */
const tokenStorage = () => sessionStorage

function clearLegacyLocalTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// Drop old shared localStorage tokens — they caused cross-tab account switching.
clearLegacyLocalTokens()

export function getTokens() {
  const storage = tokenStorage()
  return {
    access: storage.getItem(ACCESS_KEY),
    refresh: storage.getItem(REFRESH_KEY),
  }
}

export function clearTokens() {
  const storage = tokenStorage()
  storage.removeItem(ACCESS_KEY)
  storage.removeItem(REFRESH_KEY)
  clearLegacyLocalTokens()
}

export function saveTokens(access, refresh) {
  const storage = tokenStorage()
  storage.setItem(ACCESS_KEY, access)
  storage.setItem(REFRESH_KEY, refresh)
  clearLegacyLocalTokens()
}

export async function login(username, password) {
  const name = (username || '').trim()
  if (!name || !password) {
    throw new Error('Enter a username and password.')
  }
  let res
  try {
    res = await fetch(`${API_BASE}/api/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: name, password }),
    })
  } catch {
    throw networkError()
  }
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error('Too many sign-in attempts. Wait a minute and try again.')
    }
    if (res.status === 401 || res.status === 400) {
      const detail = await parseResponseError(res)
      throw new Error(
        detail && detail !== `Request failed: ${res.status}`
          ? detail
          : 'Username or password is incorrect.',
      )
    }
    throw new Error(await parseResponseError(res))
  }
  const data = await res.json()
  try {
    saveTokens(data.access, data.refresh)
  } catch {
    throw new Error(
      'Signed in, but this browser blocked saving the session. Allow storage for this site and try again.',
    )
  }
  return data
}

export async function register({ username, email, password, display_name = '' }) {
  let res
  try {
    res = await fetch(`${API_BASE}/api/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, display_name }),
    })
  } catch {
    throw networkError()
  }
  if (!res.ok) {
    throw new Error(await parseResponseError(res))
  }
  const data = await res.json()
  try {
    saveTokens(data.access, data.refresh)
  } catch {
    throw new Error(
      'Account created, but this browser blocked saving the session. Allow storage for this site and try again.',
    )
  }
  return data
}

async function refreshAccessToken() {
  const { refresh } = getTokens()
  if (!refresh) return null
  const res = await fetch(`${API_BASE}/api/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!res.ok) {
    clearTokens()
    return null
  }
  const data = await res.json()
  saveTokens(data.access, refresh)
  return data.access
}

function networkError() {
  return new Error(
    `Cannot reach the API at ${API_BASE}. Is Django running? (python manage.py runserver)`,
  )
}

/** Read error body once — Response bodies cannot be consumed twice. */
async function parseResponseError(res) {
  const text = await res.text()
  const looksHtml = /^\s*</.test(text)
  if (looksHtml) {
    if (res.status === 404) {
      return 'This API route is missing on the server (404). Redeploy the Django API so it matches this frontend.'
    }
    return `Request failed (${res.status}).`
  }
  let message = text || `Request failed: ${res.status}`
  try {
    const json = JSON.parse(text)
    if (json.detail) message = json.detail
    else if (json.message) message = json.message
    else if (typeof json === 'object' && json !== null) {
      const parts = []
      for (const [key, val] of Object.entries(json)) {
        if (Array.isArray(val)) parts.push(`${key}: ${val.join(' ')}`)
        else if (typeof val === 'string') parts.push(val)
      }
      if (parts.length) message = parts.join(' ')
    }
  } catch {
    // keep raw text
  }
  return message
}

/**
 * Fetch with a single 401 retry after refreshing the access token.
 * buildInit(accessToken) must return a fresh RequestInit each call so FormData
 * bodies are not reused after consumption.
 */
async function fetchWithAuthRetry(path, buildInit) {
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, buildInit())
  } catch {
    throw networkError()
  }

  if (res.status === 401 && getTokens().refresh) {
    const newAccess = await refreshAccessToken()
    if (newAccess) {
      try {
        res = await fetch(`${API_BASE}${path}`, buildInit(newAccess))
      } catch {
        throw networkError()
      }
    }
  }

  return res
}

export async function apiFetch(path, options = {}) {
  const buildInit = (accessOverride) => {
    const { access } = getTokens()
    const token = accessOverride ?? access
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }
    if (token) headers.Authorization = `Bearer ${token}`
    return { ...options, headers }
  }

  const res = await fetchWithAuthRetry(path, buildInit)
  if (!res.ok) {
    throw new Error(await parseResponseError(res))
  }

  if (res.status === 204) return null
  return res.json()
}

/** Multipart upload — do not set Content-Type; browser adds the boundary. */
export async function apiUpload(path, formData, options = {}) {
  // Snapshot entries before the first fetch — FormData streams are consumed once.
  const formEntries = [...formData.entries()]

  const buildInit = (accessOverride) => {
    const { access } = getTokens()
    const token = accessOverride ?? access
    const headers = { ...(options.headers || {}) }
    if (token) headers.Authorization = `Bearer ${token}`

    const body = new FormData()
    for (const [key, value] of formEntries) {
      body.append(key, value)
    }

    return {
      method: options.method || 'POST',
      ...options,
      headers,
      body,
    }
  }

  const res = await fetchWithAuthRetry(path, buildInit)
  if (!res.ok) {
    throw new Error(await parseResponseError(res))
  }

  if (res.status === 204) return null
  return res.json()
}

/** Authenticated file download (homework attachments). */
export async function apiDownload(path, filename) {
  const buildInit = (accessOverride) => {
    const { access } = getTokens()
    const token = accessOverride ?? access
    const headers = {}
    if (token) headers.Authorization = `Bearer ${token}`
    return { headers }
  }

  const res = await fetchWithAuthRetry(path, buildInit)
  if (!res.ok) {
    throw new Error(await parseResponseError(res))
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || 'download'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function getMe() {
  return apiFetch('/api/me/')
}

/** Load profile and sync browser timezone when profile still uses UTC. */
export async function loadMeProfile() {
  const me = await getMe()
  const browserTz = browserTimezone()
  if (browserTz && browserTz !== 'UTC' && (!me.timezone || me.timezone === 'UTC')) {
    try {
      return await updateMe({ timezone: browserTz })
    } catch {
      return me
    }
  }
  return me
}

export function updateMe(payload) {
  return apiFetch('/api/me/', { method: 'PATCH', body: JSON.stringify(payload) })
}

export function changePassword(currentPassword, newPassword) {
  return apiFetch('/api/me/password/', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}
