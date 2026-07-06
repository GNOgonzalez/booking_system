import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const FALLBACK = [
  { key: 'grammar', label: 'Grammar', sort_order: 1, subject: '', min_score: 0, max_score: 5 },
  { key: 'reading', label: 'Reading', sort_order: 2, subject: '', min_score: 0, max_score: 5 },
  { key: 'writing', label: 'Writing', sort_order: 3, subject: '', min_score: 0, max_score: 5 },
  { key: 'speaking', label: 'Speaking', sort_order: 4, subject: '', min_score: 0, max_score: 5 },
]

const COLORS = ['#2d5296', '#4a82d4', '#9cc2ee', '#1f8a5b', '#c45c26', '#6b4fa0', '#c4302b', '#2a9d8f', '#e9c46a', '#264653']

/** Integer options for a metric's configured range. */
export function scoreOptions(dim) {
  const min = dim?.min_score ?? 0
  const max = dim?.max_score ?? 5
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
}

/** Sensible default when opening a report form. */
export function defaultScore(dim) {
  const opts = scoreOptions(dim)
  return opts[Math.floor(opts.length / 2)] ?? opts[0] ?? 0
}

export function emptyScores(dimensions) {
  return Object.fromEntries(dimensions.map((d) => [d.key, defaultScore(d)]))
}

/** Read a score from feedback using the dimension key. */
export function scoreValue(feedback, dim) {
  if (!feedback || !dim) return dim?.min_score ?? 0
  if (feedback.scores && feedback.scores[dim.key] !== undefined) {
    return feedback.scores[dim.key]
  }
  const legacy = `${dim.key}_stars`
  return feedback[legacy] ?? dim.min_score ?? 0
}

/** Chart axis bounds for a set of metrics. */
export function scoreChartBounds(dimensions) {
  if (!dimensions.length) return { min: 0, max: 5 }
  return {
    min: Math.min(...dimensions.map((d) => d.min_score ?? 0)),
    max: Math.max(...dimensions.map((d) => d.max_score ?? 5)),
  }
}

/** Active metric definitions — optional subject scopes to class subject. */
export function useScoreDimensions(subject = '') {
  const [dimensions, setDimensions] = useState(FALLBACK)
  const subjectKey = subject || ''

  useEffect(() => {
    const qs = subjectKey ? `?subject=${encodeURIComponent(subjectKey)}` : ''
    apiFetch(`/api/progress/score-dimensions/${qs}`)
      .then((rows) => {
        if (rows.length) setDimensions(rows)
        else if (!subjectKey) setDimensions(FALLBACK)
        else setDimensions([])
      })
      .catch(() => {
        if (!subjectKey) setDimensions(FALLBACK)
      })
  }, [subjectKey])

  return dimensions.map((d, i) => ({
    ...d,
    min_score: d.min_score ?? 0,
    max_score: d.max_score ?? 5,
    color: COLORS[i % COLORS.length],
  }))
}
