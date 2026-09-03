import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Suspense, lazy, useEffect, useState } from 'react'
import { clearTokens, getTokens, loadMeProfile, login, register } from './api.js'
import LoginPage from './pages/LoginPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import BlogFeed from './components/BlogFeed.jsx'
import OnboardingChecklist from './components/OnboardingChecklist.jsx'
import { BrandingProvider, useBranding } from './hooks/useBranding.jsx'
import { GlossaryProvider, useGlossary } from './hooks/useGlossary.jsx'
import { applyTheme } from './hooks/useTheme.js'

const ProfilePage = lazy(() => import('./pages/ProfilePage.jsx'))
const StudentSessionsPage = lazy(() => import('./pages/StudentSessionsPage.jsx'))
const StudentRequestClassPage = lazy(() => import('./pages/StudentRequestClassPage.jsx'))
const StudentBookingsPage = lazy(() => import('./pages/StudentBookingsPage.jsx'))
const StudentProgressPage = lazy(() => import('./pages/StudentProgressPage.jsx'))
const StudentHomeworkPage = lazy(() => import('./pages/StudentHomeworkPage.jsx'))
const MembershipPage = lazy(() => import('./pages/MembershipPage.jsx'))
const TeacherSessionsPage = lazy(() => import('./pages/TeacherSessionsPage.jsx'))
const TeacherCreateSessionPage = lazy(() => import('./pages/TeacherCreateSessionPage.jsx'))
const TeacherAvailabilityPage = lazy(() => import('./pages/TeacherAvailabilityPage.jsx'))
const TeacherClassesPage = lazy(() => import('./pages/TeacherClassesPage.jsx'))
const TeacherProgressPage = lazy(() => import('./pages/TeacherProgressPage.jsx'))
const TeacherHomeworkPage = lazy(() => import('./pages/TeacherHomeworkPage.jsx'))
const TeacherCurriculumPage = lazy(() => import('./pages/TeacherCurriculumPage.jsx'))
const TeacherClassRequestsPage = lazy(() => import('./pages/TeacherClassRequestsPage.jsx'))
const StaffDashboardPage = lazy(() => import('./pages/StaffDashboardPage.jsx'))
const StaffMetricsPage = lazy(() => import('./pages/StaffMetricsPage.jsx'))
const StaffSchedulePage = lazy(() => import('./pages/StaffSchedulePage.jsx'))
const StaffTeacherLayout = lazy(() => import('./pages/StaffTeacherLayout.jsx'))
const StaffClassCatalogPage = lazy(() => import('./pages/StaffClassCatalogPage.jsx'))
const StaffCurriculumPage = lazy(() => import('./pages/StaffCurriculumPage.jsx'))
const StaffCreateClassPage = lazy(() => import('./pages/StaffCreateClassPage.jsx'))
const StaffClassRequestsPage = lazy(() => import('./pages/StaffClassRequestsPage.jsx'))
const StaffStudentsPage = lazy(() => import('./pages/StaffStudentsPage.jsx'))
const StaffStudentMembershipPage = lazy(() => import('./pages/StaffStudentMembershipPage.jsx'))
const StaffPaymentsPage = lazy(() => import('./pages/StaffPaymentsPage.jsx'))
const StaffIntegrationsPage = lazy(() => import('./pages/StaffIntegrationsPage.jsx'))
const StaffActivityPage = lazy(() => import('./pages/StaffActivityPage.jsx'))
const StaffTeacherPermissionsPage = lazy(() => import('./pages/StaffTeacherPermissionsPage.jsx'))
const StaffTeacherStudentsPage = lazy(() => import('./pages/StaffTeacherStudentsPage.jsx'))
const InboxPage = lazy(() => import('./pages/InboxPage.jsx'))
const CurriculumPage = lazy(() => import('./pages/CurriculumPage.jsx'))
const StaffGlossaryPage = lazy(() => import('./pages/StaffGlossaryPage.jsx'))
const StaffLLMSettingsPage = lazy(() => import('./pages/StaffLLMSettingsPage.jsx'))
const StaffMembershipPlansPage = lazy(() => import('./pages/StaffMembershipPlansPage.jsx'))
const StaffReportsPage = lazy(() => import('./pages/StaffReportsPage.jsx'))
const StaffBrandingPage = lazy(() => import('./pages/StaffBrandingPage.jsx'))
const BlogManagePage = lazy(() => import('./pages/BlogManagePage.jsx'))
const StudentHomeDashboard = lazy(() => import('./pages/StudentHomeDashboard.jsx'))

function PageLoader() {
  return <p className="page-intro">Loading…</p>
}

function MobileTopbar({ onOpen }) {
  const { branding } = useBranding()
  return (
    <header className="mobile-topbar">
      <button type="button" className="mobile-nav-toggle" aria-label="Open menu" onClick={onOpen}>
        <span className="mobile-nav-toggle-icon" aria-hidden="true" />
      </button>
      <div className="mobile-topbar-brand">
        {branding.logo_url && (
          <img src={branding.logo_url} alt="" className="branding-logo branding-logo--sidebar" />
        )}
        <span>{branding.display_name}</span>
      </div>
    </header>
  )
}

function Sidebar({ me, onLogout, onClose, collapsed, onToggleCollapse }) {
  const { label, labels } = useGlossary()
  const { branding } = useBranding()
  const roles = me?.roles || []
  const isStudent = roles.includes('student')
  const isTeacher = roles.includes('teacher')
  const isStaff = roles.includes('staff')
  const displayName = me?.display_name || me?.username || 'Account'
  const tp = me?.teacher_permissions
  const can = (key) => !tp || tp[key] !== false
  const canManageBlog = isStaff || (isTeacher && can('manage_blog'))

  return (
    <aside className="sidebar" aria-expanded={!collapsed}>
      <div className="sidebar-toolbar">
        <button type="button" className="sidebar-close" aria-label="Close menu" onClick={onClose}>
          ×
        </button>
        <button
          type="button"
          className="sidebar-collapse-btn"
          aria-label={collapsed ? 'Expand menu' : 'Collapse menu'}
          title={collapsed ? 'Expand menu' : 'Collapse menu'}
          onClick={onToggleCollapse}
        >
          <span aria-hidden="true">{collapsed ? '›' : '‹'}</span>
        </button>
      </div>
      <div className="brand">
        {branding.logo_url && (
          <img src={branding.logo_url} alt="" className="branding-logo branding-logo--sidebar" />
        )}
        <span>{branding.display_name}</span>
      </div>

      <NavLink to="/" end className="nav-link">Home</NavLink>
      {canManageBlog && (
        <NavLink to="/blog/manage" className="nav-link">Blog posts</NavLink>
      )}

      {isStudent && (
        <>
          <div className="nav-section">{label('student')}</div>
          <NavLink to="/sessions" className="nav-link">Book a lesson</NavLink>
          <NavLink to="/sessions/request" className="nav-link">Request a class</NavLink>
          <NavLink to="/bookings" className="nav-link">My {labels('booking').toLowerCase()}</NavLink>
          <NavLink to="/membership" className="nav-link">Membership</NavLink>
          <NavLink to="/progress" className="nav-link">My progress</NavLink>
          <NavLink to="/homework" className="nav-link">Homework</NavLink>
        </>
      )}

      {isStaff && (
        <>
          <div className="nav-section">Staff</div>
          <NavLink to="/staff" end className="nav-link">Dashboard</NavLink>
          <NavLink to="/staff/schedule" className="nav-link">{label('studio')} schedule</NavLink>
          <NavLink to="/staff/requests" className="nav-link">Class requests</NavLink>
          <NavLink to="/staff/classes/new" className="nav-link">Create {label('class').toLowerCase()}</NavLink>
          <NavLink to="/staff/class-catalog" className="nav-link">Class roadmap</NavLink>
          <NavLink to="/staff/curriculum" className="nav-link">Curriculum</NavLink>
          <NavLink to="/staff/students" className="nav-link">{labels('student')}</NavLink>
          <NavLink to="/staff/memberships" className="nav-link">Memberships</NavLink>
          <NavLink to="/staff/payments" className="nav-link">Payments</NavLink>
          <NavLink to="/staff/integrations" className="nav-link">Integrations</NavLink>
          <NavLink to="/staff/reports" className="nav-link">Reports</NavLink>
          <NavLink to="/staff/activity" className="nav-link">Staff activity</NavLink>
          <NavLink to="/staff/metrics" className="nav-link">{label('studio')} {labels('metric').toLowerCase()}</NavLink>
          <NavLink to="/staff/glossary" className="nav-link">Glossary</NavLink>
          <NavLink to="/staff/branding" className="nav-link">Sign-in branding</NavLink>
          <NavLink to="/staff/ai" className="nav-link">AI settings</NavLink>
        </>
      )}

      {isTeacher && (
        <>
          <div className="nav-section">{label('teacher')}</div>
          <NavLink to="/teacher/sessions" className="nav-link">My {labels('session').toLowerCase()}</NavLink>
          <NavLink to="/teacher/requests" className="nav-link">Class requests</NavLink>
          {can('manage_schedule') && (
            <NavLink to="/teacher/sessions/new" className="nav-link">New {label('session').toLowerCase()}</NavLink>
          )}
          <NavLink to="/teacher/classes" className="nav-link">{labels('class')}</NavLink>
          {can('manage_availability') && (
            <NavLink to="/teacher/availability" className="nav-link">{label('availability')}</NavLink>
          )}
          <NavLink to="/teacher/progress" className="nav-link">{label('student')} {labels('report').toLowerCase()}</NavLink>
          {can('assign_homework') && (
            <NavLink to="/teacher/homework" className="nav-link">Homework</NavLink>
          )}
          <NavLink to="/teacher/curriculum" className="nav-link">Curriculum</NavLink>
        </>
      )}

      <div className="nav-section">Account</div>
      <NavLink to="/inbox" className="nav-link">Inbox</NavLink>
      <NavLink to="/curriculum" className="nav-link">Curriculum</NavLink>
      <NavLink to="/profile" className="nav-link">Profile & settings</NavLink>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          {displayName}
          {roles.map((role) => (
            <span key={role}> · <span className="badge">{role}</span></span>
          ))}
        </div>
        <button type="button" className="ghost" onClick={onLogout}>Log out</button>
      </div>
    </aside>
  )
}

function HomePage({ me }) {
  const roles = me?.roles || []
  const { label, labels } = useGlossary()
  // Each role contributes its own section: someone who both teaches and studies gets both.
  const isStudent = roles.includes('student')
  const isStaff = roles.includes('staff')
  const isTeacher = roles.includes('teacher')
  const hasAnyRole = isStudent || isStaff || isTeacher
  const tp = me?.teacher_permissions
  const can = (key) => !tp || tp[key] !== false
  const canManageBlog = isStaff || (isTeacher && can('manage_blog'))

  const intro = () => {
    const parts = []
    if (isStaff) {
      parts.push(`manage ${labels('teacher').toLowerCase()}, schedules, and ${label('studio').toLowerCase()}-wide settings`)
    }
    if (isTeacher) {
      parts.push(`run your ${labels('session').toLowerCase()} and ${label('student').toLowerCase()} progress`)
    }
    if (isStudent) {
      parts.push('book lessons and track your own progress')
    }
    if (!parts.length) return 'Use the menu on the left to get started.'
    if (parts.length === 1) return `Your home base to ${parts[0]}.`
    return `Your home base to ${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}.`
  }

  return (
    <div>
      <h1>Welcome{me?.display_name ? `, ${me.display_name}` : ''}</h1>
      <p className="page-intro">{intro()}</p>

      <BlogFeed canManage={canManageBlog} />

      <OnboardingChecklist />

      {isStudent && (
        <Suspense fallback={<PageLoader />}>
          <StudentHomeDashboard />
        </Suspense>
      )}

      {isStaff && (
        <div className="card">
          <div className="card-title">Staff tools</div>
          <p className="card-meta">
            Manage any teacher&apos;s schedule, approve class requests, and edit metric names.
          </p>
          <div className="form-actions">
            <NavLink to="/staff" className="btn secondary">Open staff dashboard</NavLink>
            <NavLink to="/staff/requests" className="btn secondary">Pending class requests</NavLink>
          </div>
        </div>
      )}

      {isTeacher && (
        <div className="card">
          <div className="card-title">{label('teacher')} tools</div>
          <p className="card-meta">
            Your {labels('session').toLowerCase()}, class requests, and {label('student').toLowerCase()} reports.
          </p>
          <div className="form-actions">
            <NavLink to="/teacher/sessions" className="btn secondary">
              My {labels('session').toLowerCase()}
            </NavLink>
            <NavLink to="/teacher/requests" className="btn secondary">Class requests</NavLink>
            {can('manage_schedule') && (
              <NavLink to="/teacher/sessions/new" className="btn secondary">
                New {label('session').toLowerCase()}
              </NavLink>
            )}
          </div>
        </div>
      )}

      {!hasAnyRole && (
        <div className="card">
          <div className="card-title">Getting started</div>
          <p className="card-meta">
            Your account has no role yet. Ask staff to add you as a {label('student').toLowerCase()}.
          </p>
        </div>
      )}
    </div>
  )
}

const SIDEBAR_COLLAPSED_KEY = 'sidebarCollapsed'

function AppRoutes() {
  const navigate = useNavigate()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
    } catch {
      return false
    }
  })
  const [authed, setAuthed] = useState(Boolean(getTokens().access))
  const [me, setMe] = useState(null)

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((current) => {
      const next = !current
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0')
      } catch {
        // ignore quota / private mode
      }
      return next
    })
  }

  useEffect(() => {
    setNavOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!navOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setNavOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navOpen])

  useEffect(() => {
    document.body.style.overflow = navOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [navOpen])

  const loadMe = () => {
    if (getTokens().access) {
      loadMeProfile().then(setMe).catch(() => setMe(null))
    }
  }

  useEffect(() => {
    loadMe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed])

  useEffect(() => {
    if (me?.theme) {
      applyTheme(me.theme)
    }
  }, [me?.theme])

  useEffect(() => {
    if (!me || me.theme !== 'system') return undefined
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [me?.theme])

  const handleLogin = async (username, password) => {
    await login(username, password)
    setAuthed(true)
    navigate('/')
  }

  const handleRegister = async (payload) => {
    await register(payload)
    setAuthed(true)
    navigate('/')
  }

  const handleLogout = () => {
    clearTokens()
    setMe(null)
    setAuthed(false)
    navigate('/login')
  }

  if (!authed) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/register" element={<RegisterPage onRegister={handleRegister} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <GlossaryProvider>
      <div className={`app-shell${navOpen ? ' nav-open' : ''}${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
        <MobileTopbar onOpen={() => setNavOpen(true)} />
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          tabIndex={navOpen ? 0 : -1}
          onClick={() => setNavOpen(false)}
        />
        <Sidebar
          me={me}
          onLogout={handleLogout}
          onClose={() => setNavOpen(false)}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapsed}
        />
        <main className="main">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<HomePage me={me} />} />
              <Route path="/blog/manage" element={<BlogManagePage />} />
              <Route path="/sessions" element={<StudentSessionsPage />} />
              <Route path="/sessions/request" element={<StudentRequestClassPage />} />
              <Route path="/bookings" element={<StudentBookingsPage />} />
              <Route path="/membership" element={<MembershipPage />} />
              <Route path="/progress" element={<StudentProgressPage />} />
              <Route path="/homework" element={<StudentHomeworkPage />} />
              <Route path="/teacher/sessions" element={<TeacherSessionsPage />} />
              <Route path="/teacher/requests" element={<TeacherClassRequestsPage />} />
              <Route path="/teacher/sessions/new" element={<TeacherCreateSessionPage />} />
              <Route path="/teacher/classes" element={<TeacherClassesPage />} />
              <Route path="/teacher/availability" element={<TeacherAvailabilityPage />} />
              <Route path="/teacher/progress" element={<TeacherProgressPage />} />
              <Route path="/teacher/homework" element={<TeacherHomeworkPage />} />
              <Route path="/teacher/curriculum" element={<TeacherCurriculumPage />} />
              <Route path="/staff" element={<StaffDashboardPage />} />
              <Route path="/staff/schedule" element={<StaffSchedulePage />} />
              <Route path="/staff/requests" element={<StaffClassRequestsPage />} />
              <Route path="/staff/classes/new" element={<StaffCreateClassPage />} />
              <Route path="/staff/class-catalog" element={<StaffClassCatalogPage />} />
              <Route path="/staff/curriculum" element={<StaffCurriculumPage />} />
              <Route path="/staff/students" element={<StaffStudentsPage />} />
              <Route path="/staff/students/:studentId" element={<StaffStudentMembershipPage />} />
              <Route path="/staff/memberships" element={<StaffMembershipPlansPage />} />
              <Route path="/staff/payments" element={<StaffPaymentsPage />} />
              <Route path="/staff/integrations" element={<StaffIntegrationsPage />} />
              <Route path="/staff/activity" element={<StaffActivityPage />} />
              <Route path="/staff/reports" element={<StaffReportsPage />} />
              <Route path="/staff/metrics" element={<StaffMetricsPage />} />
              <Route path="/staff/glossary" element={<StaffGlossaryPage />} />
              <Route path="/staff/branding" element={<StaffBrandingPage />} />
              <Route path="/staff/ai" element={<StaffLLMSettingsPage />} />
              <Route path="/staff/teachers/:teacherId" element={<StaffTeacherLayout />}>
                <Route index element={<Navigate to="sessions" replace />} />
                <Route path="sessions" element={<TeacherSessionsPage />} />
                <Route path="requests" element={<TeacherClassRequestsPage />} />
                <Route path="sessions/new" element={<TeacherCreateSessionPage />} />
                <Route path="classes" element={<TeacherClassesPage />} />
                <Route path="availability" element={<TeacherAvailabilityPage />} />
                <Route path="progress" element={<TeacherProgressPage />} />
                <Route path="homework" element={<TeacherHomeworkPage />} />
                <Route path="curriculum" element={<TeacherCurriculumPage />} />
                <Route path="students" element={<StaffTeacherStudentsPage />} />
                <Route path="permissions" element={<StaffTeacherPermissionsPage />} />
              </Route>
              <Route path="/inbox" element={<InboxPage />} />
              <Route path="/curriculum" element={<CurriculumPage />} />
              <Route path="/profile" element={<ProfilePage onSaved={loadMe} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </GlossaryProvider>
  )
}

export default function App() {
  return (
    <BrandingProvider>
      <AppRoutes />
    </BrandingProvider>
  )
}
