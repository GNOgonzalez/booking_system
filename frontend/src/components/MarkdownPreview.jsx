import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../api.js'

/**
 * Live preview of Markdown source, rendered server-side through the same
 * sanitization pipeline used at publish time (so preview always matches output).
 */
export function useMarkdownPreview(source, { debounceMs = 500 } = {}) {
  const [html, setHtml] = useState('')
  const timer = useRef(null)
  const latest = useRef('')

  useEffect(() => {
    latest.current = source
    if (!source || !source.trim()) {
      setHtml('')
      return undefined
    }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      apiFetch('/api/markdown/preview/', {
        method: 'POST',
        body: JSON.stringify({ body: source }),
      })
        .then((data) => {
          if (latest.current === source) setHtml(data.html || '')
        })
        .catch(() => {})
    }, debounceMs)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [source, debounceMs])

  return html
}

/** Rendered HTML from the server-side sanitizer — safe to inject. */
export function MarkdownBody({ html, className = '' }) {
  if (!html) return null
  return (
    <div
      className={`markdown-body ${className}`.trim()}
      // Server output is sanitized with a bleach allowlist (scheduling/services/markdown.py).
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default function MarkdownPreview({ source }) {
  const html = useMarkdownPreview(source)
  if (!source || !source.trim()) return null
  return (
    <div className="markdown-preview">
      <div className="card-meta">Preview</div>
      {html ? (
        <MarkdownBody html={html} />
      ) : (
        <p className="card-meta">Rendering…</p>
      )}
    </div>
  )
}
