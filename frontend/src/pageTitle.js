/** Short title for the top bar. Longest prefix wins. */
const TITLES = [
  ['/staff/class-catalog', 'Curriculum'],
  ['/staff/classes/new', 'Create class'],
  ['/staff/curriculum', 'Curriculum'],
  ['/staff/memberships', 'Memberships'],
  ['/staff/integrations', 'Integrations'],
  ['/staff/branches', 'Branches'],
  ['/staff/schedule', 'Schedule'],
  ['/staff/requests', 'Class requests'],
  ['/staff/students', 'Students'],
  ['/staff/payments', 'Payments'],
  ['/staff/activity', 'Staff activity'],
  ['/staff/reports', 'Reports'],
  ['/staff/metrics', 'Metrics'],
  ['/staff/glossary', 'Glossary'],
  ['/staff/branding', 'Branding'],
  ['/staff/ai', 'AI settings'],
  ['/staff/teachers', 'Teacher'],
  ['/staff', 'Studio'],
  ['/teacher/sessions/new', 'New session'],
  ['/teacher/sessions', 'My sessions'],
  ['/teacher/requests', 'Class requests'],
  ['/teacher/classes', 'Classes'],
  ['/teacher/availability', 'Availability'],
  ['/teacher/progress', 'Reports'],
  ['/teacher/homework', 'Homework'],
  ['/teacher/curriculum', 'Curriculum'],
  ['/sessions/request', 'Request a class'],
  ['/sessions', 'Book a lesson'],
  ['/bookings', 'My bookings'],
  ['/membership', 'Membership'],
  ['/progress', 'My progress'],
  ['/homework', 'Homework'],
  ['/curriculum', 'My curriculum'],
  ['/blog/manage', 'Blog posts'],
  ['/inbox', 'Inbox'],
  ['/profile', 'Profile'],
  ['/', 'Home'],
]

export function titleForPath(pathname) {
  const path = pathname.replace(/\/$/, '') || '/'
  for (const [prefix, title] of TITLES) {
    if (path === prefix || (prefix !== '/' && path.startsWith(`${prefix}/`))) {
      return title
    }
  }
  return ''
}
