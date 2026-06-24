import { FormEvent, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiDelete, apiGet, apiPatch, apiPost } from '../lib/api'
import type { AlertSubscription, Country, Paginated } from '../lib/api'
import { useAuth } from '../lib/auth'

const CATEGORIES = [
  { value: '', label: 'All categories' },
  { value: 'tax', label: 'Tax' },
  { value: 'customs', label: 'Customs' },
  { value: 'investment', label: 'Investment' },
  { value: 'eac_trade', label: 'EAC Trade' },
  { value: 'labor', label: 'Labor' },
]

export default function AlertsPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [alerts, setAlerts] = useState<AlertSubscription[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [countryCode, setCountryCode] = useState(searchParams.get('country') ?? '')
  const [category, setCategory] = useState(searchParams.get('category') ?? '')
  function loadAlerts() {
    apiGet<Paginated<AlertSubscription>>('/regulatory/alerts/')
      .then((data) => setAlerts(data.results))
      .catch(() => setError('Unable to load alert subscriptions.'))
  }

  useEffect(() => {
    if (!user) return
    loadAlerts()
    apiGet<Paginated<Country>>('/countries/').then((c) => setCountries(c.results)).catch(() => {})
  }, [user])

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPost('/regulatory/alerts/', {
        email: form.get('email'),
        country_code: countryCode,
        category,
      })
      setCountryCode('')
      setCategory('')
      e.currentTarget.reset()
      loadAlerts()
    } catch {
      setError('Failed to create alert subscription.')
    } finally {
      setLoading(false)
    }
  }

  async function toggleAlert(alert: AlertSubscription) {
    try {
      await apiPatch(`/regulatory/alerts/${alert.id}/`, { is_active: !alert.is_active })
      loadAlerts()
    } catch {
      setError('Failed to update subscription.')
    }
  }

  async function removeAlert(id: number) {
    try {
      await apiDelete(`/regulatory/alerts/${id}/`)
      loadAlerts()
    } catch {
      setError('Failed to remove subscription.')
    }
  }

  if (!user) {
    return (
      <div className="page">
        <header className="page-header"><h1>Change Alerts</h1></header>
        <div className="card">
          <p><Link to="/login">Sign in</Link> to manage regulatory change alerts for your organization.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Change Alerts</h1>
        <p className="lead">Get notified when regulatory rules update in your target markets.</p>
      </header>

      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Email
          <input name="email" type="email" required defaultValue={user.email || ''} />
        </label>
        <label>
          Country (optional)
          <select name="country_code" value={countryCode} onChange={(e) => setCountryCode(e.target.value)}>
            <option value="">All EAC countries</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>
          Category (optional)
          <select name="category" value={category} onChange={(e) => setCategory(e.target.value)}>            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>{cat.label}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={loading}>{loading ? 'Saving…' : 'Subscribe'}</button>
      </form>

      {error && <p className="error">{error}</p>}

      {alerts.length === 0 && !error && (
        <div className="empty-state card">
          <p>No alert subscriptions yet. Add one above to get notified on regulatory changes.</p>
        </div>
      )}

      <div className="list">
        {alerts.map((alert) => (
          <article key={alert.id} className="card list-item">
            <div className="list-item-header">
              {alert.country && <span className="badge">{alert.country.code}</span>}
              {alert.category && <span className="badge">{alert.category}</span>}
              <span className={`badge ${alert.is_active ? '' : 'muted'}`}>
                {alert.is_active ? 'active' : 'paused'}
              </span>
            </div>
            <h2>{alert.email}</h2>
            <p className="muted">Created {new Date(alert.created_at).toLocaleDateString()}</p>
            <div className="card-actions">
              <button type="button" className="text-btn" onClick={() => toggleAlert(alert)}>
                {alert.is_active ? 'Pause' : 'Resume'}
              </button>
              <button type="button" className="text-btn danger" onClick={() => removeAlert(alert.id)}>
                Remove
              </button>
            </div>
          </article>
        ))}      </div>
    </div>
  )
}
