import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

let cached = null

/** Shared homework and blog upload size limits from the API. */
export function useUploadLimits() {
  const [limits, setLimits] = useState(cached)

  useEffect(() => {
    if (cached) {
      setLimits(cached)
      return
    }
    apiFetch('/api/upload-limits/')
      .then((data) => {
        cached = data
        setLimits(data)
      })
      .catch(() => {})
  }, [])

  return limits
}

export function homeworkFileHint(limits) {
  if (!limits) return null
  const exts = (limits.homework_extensions || []).join(', ')
  return `Max ${limits.homework_max_mb} MB${exts ? ` · ${exts}` : ''}`
}

export function blogImageHint(limits) {
  if (!limits) return null
  const exts = (limits.blog_image_extensions || []).join(', ')
  return `Max ${limits.blog_image_max_mb} MB${exts ? ` · ${exts}` : ''}`
}
