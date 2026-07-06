/** Apply light/dark theme via CSS variables on document.documentElement. */

function resolveTheme(preference) {
  if (preference === 'dark') return 'dark'
  if (preference === 'light') return 'light'
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function applyTheme(preference = 'system') {
  if (typeof document === 'undefined') return
  document.documentElement.dataset.theme = resolveTheme(preference)
}

export function useTheme(preference) {
  // Hook body kept for future listeners; App applies theme when `me` loads.
  applyTheme(preference || 'system')
}
