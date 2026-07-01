const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export function getTokens() {
  return {
    access: localStorage.getItem('accessToken'),
    refresh: localStorage.getItem('refreshToken'),
  }
}

export function clearTokens() {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
}

export function saveTokens(access, refresh) {
  localStorage.setItem('accessToken', access)
  localStorage.setItem('refreshToken', refresh)
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    throw new Error('Login failed')
  }
  const data = await res.json()
  saveTokens(data.access, data.refresh)
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

export async function apiFetch(path, options = {}) {
  const { access } = getTokens()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  if (access) {
    headers.Authorization = `Bearer ${access}`
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401 && getTokens().refresh) {
    const newAccess = await refreshAccessToken()
    if (newAccess) {
      headers.Authorization = `Bearer ${newAccess}`
      res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    }
  }

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export function getMe() {
  return apiFetch('/api/me/')
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
