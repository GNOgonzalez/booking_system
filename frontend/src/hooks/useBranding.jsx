import { createContext, useContext, useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const DEFAULT_BRANDING = {
  display_name: 'Booking Studio',
  logo_url: null,
}

const BrandingContext = createContext({
  branding: DEFAULT_BRANDING,
  loaded: false,
  reload: () => {},
})

let cachedBranding = null

async function fetchBranding() {
  const res = await fetch(`${API_BASE}/api/branding/`)
  if (!res.ok) {
    throw new Error('Failed to load branding')
  }
  return res.json()
}

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState(cachedBranding || DEFAULT_BRANDING)
  const [loaded, setLoaded] = useState(Boolean(cachedBranding))

  const load = () => {
    fetchBranding()
      .then((data) => {
        cachedBranding = data
        setBranding(data)
        setLoaded(true)
      })
      .catch(() => setLoaded(true))
  }

  useEffect(load, [])

  return (
    <BrandingContext.Provider value={{ branding, loaded, reload: load }}>
      {children}
    </BrandingContext.Provider>
  )
}

export function useBranding() {
  return useContext(BrandingContext)
}

export function clearBrandingCache() {
  cachedBranding = null
}
