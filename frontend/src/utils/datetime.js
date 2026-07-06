/** Browser-local datetime helpers — API uses ISO UTC; UI uses local time. */

export function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

export function timezoneLabel(tz = browserTimezone()) {
  try {
    const parts = new Intl.DateTimeFormat(undefined, {
      timeZone: tz,
      timeZoneName: 'short',
    }).formatToParts(new Date())
    return parts.find((part) => part.type === 'timeZoneName')?.value || tz
  } catch {
    return tz
  }
}

/** `datetime-local` value from an ISO timestamp (local wall clock). */
export function toDatetimeLocal(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** ISO UTC for API from a `datetime-local` value (interpreted as local time). */
export function datetimeLocalToIso(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toISOString()
}

export function formatDateTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatSlotRange(startIso, endIso) {
  if (!startIso || !endIso) return ''
  const start = new Date(startIso)
  const end = new Date(endIso)
  const date = start.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
  const fmt = (value) => value.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
  const tz = timezoneLabel()
  return `${date} · ${fmt(start)} – ${fmt(end)} ${tz}`
}

export function endFromStartDuration(startValue, durationMinutes) {
  if (!startValue) return ''
  const startDate = new Date(startValue)
  if (Number.isNaN(startDate.getTime())) return ''
  return toDatetimeLocal(new Date(startDate.getTime() + durationMinutes * 60 * 1000).toISOString())
}
