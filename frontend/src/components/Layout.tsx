import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { SITE_TAGLINE } from '../lib/siteCopy'
import './Layout.css'
const navItems = [
  { to: '/', label: 'Overview', end: true },
  { to: '/assistant', label: 'Proof-Based Assistant' },
  { to: '/regulatory', label: 'Regulatory Changes' },
  { to: '/alerts', label: 'Change Alerts' },
  { to: '/trade', label: 'Trade Procedures' },
  { to: '/playbooks', label: 'Market Entry' },
  { to: '/vendors', label: 'Vendor Due Diligence' },
  { to: '/intelligence', label: 'Economic Intelligence' },
]

export default function Layout() {
  const { user, logout, organizationId, setOrganizationId } = useAuth()
  const activeMembership = user?.memberships.find((m) => m.organization.id === organizationId)
  const orgName = activeMembership?.organization.name

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">EB</span>
          <div>
            <strong>EastBridge</strong>
            <small>Ops Intelligence</small>
          </div>
        </div>
        <p className="tagline">{SITE_TAGLINE}</p>        <div className="auth-bar">
          {user ? (
            <>
              {user.memberships.length > 1 ? (
                <label className="org-switcher">
                  <span className="sr-only">Organization</span>
                  <select
                    value={organizationId ?? ''}
                    onChange={(e) => setOrganizationId(Number(e.target.value))}
                  >
                    {user.memberships.map((m) => (
                      <option key={m.organization.id} value={m.organization.id}>
                        {m.organization.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <span className="auth-user">{orgName ?? user.username}</span>
              )}
              <button type="button" className="auth-btn" onClick={logout}>Sign out</button>
            </>
          ) : (
            <Link to="/login" className="auth-link">Sign in</Link>
          )}
        </div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
