import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api.js'

const DEFAULTS = {
  student: { singular: 'Student', plural: 'Students' },
  teacher: { singular: 'Teacher', plural: 'Teachers' },
  class: { singular: 'Class', plural: 'Classes' },
  session: { singular: 'Session', plural: 'Sessions' },
  booking: { singular: 'Booking', plural: 'Bookings' },
  report: { singular: 'Report', plural: 'Reports' },
  metric: { singular: 'Metric', plural: 'Metrics' },
  availability: { singular: 'Availability', plural: 'Availability' },
  studio: { singular: 'Studio', plural: 'Studio' },
}

const GlossaryContext = createContext({
  label: (key) => DEFAULTS[key]?.singular || key,
  labels: (key) => DEFAULTS[key]?.plural || key,
  terms: DEFAULTS,
})

export function GlossaryProvider({ children }) {
  const [byKey, setByKey] = useState(DEFAULTS)

  useEffect(() => {
    const load = () => {
      apiFetch('/api/glossary/')
        .then((rows) => {
          const next = { ...DEFAULTS }
          for (const row of rows) {
            next[row.key] = { singular: row.singular, plural: row.plural }
          }
          setByKey(next)
        })
        .catch(() => {})
    }
    load()
    window.addEventListener('glossary-updated', load)
    return () => window.removeEventListener('glossary-updated', load)
  }, [])

  const value = useMemo(() => ({
    terms: byKey,
    label: (key, count = 1) => {
      const t = byKey[key] || DEFAULTS[key]
      if (!t) return key
      return count === 1 ? t.singular : t.plural
    },
    labels: (key) => {
      const t = byKey[key] || DEFAULTS[key]
      return t?.plural || key
    },
  }), [byKey])

  return (
    <GlossaryContext.Provider value={value}>
      {children}
    </GlossaryContext.Provider>
  )
}

export function useGlossary() {
  return useContext(GlossaryContext)
}
