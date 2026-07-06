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

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new Error(`Cannot reach the API at ${API_BASE}. Is Django running? (python manage.py runserver)`)
  }

  if (res.status === 401 && getTokens().refresh) {
    const newAccess = await refreshAccessToken()
    if (newAccess) {
      headers.Authorization = `Bearer ${newAccess}`
      res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    }
  }

  if (!res.ok) {
    const text = await res.text()
    let message = text || `Request failed: ${res.status}`
    try {
      const json = JSON.parse(text)
      if (json.detail) message = json.detail
      else if (json.message) message = json.message
    } catch {
      // keep raw text
    }
    throw new Error(message)
  }

  if (res.status === 204) return null
  return res.json()
}

/** Multipart upload — do not set Content-Type; browser adds the boundary. */
export async function apiUpload(path, formData, options = {}) {
  const { access } = getTokens()
  const headers = { ...(options.headers || {}) }
  if (access) {
    headers.Authorization = `Bearer ${access}`
  }

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: options.method || 'POST',
      ...options,
      headers,
      body: formData,
    })
  } catch {
    throw new Error(`Cannot reach the API at ${API_BASE}. Is Django running?`)
  }

  if (res.status === 401 && getTokens().refresh) {
    const newAccess = await refreshAccessToken()
    if (newAccess) {
      headers.Authorization = `Bearer ${newAccess}`
      res = await fetch(`${API_BASE}${path}`, {
        method: options.method || 'POST',
        ...options,
        headers,
        body: formData,
      })
    }
  }

  if (!res.ok) {
    const text = await res.text()
    let message = text || `Request failed: ${res.status}`
    try {
      const json = JSON.parse(text)
      if (json.detail) message = json.detail
    } catch {
      // keep raw text
    }
    throw new Error(message)
  }

  if (res.status === 204) return null
  return res.json()
}

/** Authenticated file download (homework attachments). */
export async function apiDownload(path, filename) {
  const { access } = getTokens()
  const headers = {}
  if (access) headers.Authorization = `Bearer ${access}`

  const res = await fetch(`${API_BASE}${path}`, { headers })
  if (!res.ok) {
    throw new Error('Download failed.')
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

export function updateMe(payload) {
  return apiFetch('/api/me/', { method: 'PATCH', body: JSON.stringify(payload) })
}

export function changePassword(currentPassword, newPassword) {
  return apiFetch('/api/me/password/', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}
