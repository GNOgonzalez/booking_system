import { useEffect, useState } from 'react'
import { getMe } from '../api.js'

/** Teacher capability flags — staff controls these; teachers read from /api/me/. */
export function useTeacherPermissions() {
  const [permissions, setPermissions] = useState(null)

  useEffect(() => {
    getMe()
      .then((me) => setPermissions(me.teacher_permissions || null))
      .catch(() => setPermissions(null))
  }, [])

  const can = (key) => (permissions ? permissions[key] !== false : true)

  return { permissions, can, loaded: permissions !== null }
}
