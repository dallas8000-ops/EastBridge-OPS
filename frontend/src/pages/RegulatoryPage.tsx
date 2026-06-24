import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../lib/api'
import type { Country, Paginated, RegulatoryChange } from '../lib/api'
import { useAuth } from '../lib/auth'
import { assistantLink } from '../lib/assistantLink'

const riskColors: Record<string, string> = {
  low: '#16a34a',
  medium: '#ca8a04',
  high: '#ea580c',
  critical: '#dc2626',
}

const CATEGORIES = [
  { value: '', label: 'All categories' },
  { value: 'tax', label: 'Tax' },
  { value: 'customs', label: 'Customs' },
  { value: 'investment', label: 'Investment' },
  { value: 'eac_trade', label: 'EAC Trade' },
  { value: 'labor', label: 'Labor' },
]

const RISK_LEVELS = [
  { value: '', label: 'All risk levels' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

export default function RegulatoryPage() {
  const { user } = useAuth()
  const [changes, setChanges] = useState<RegulatoryChange[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [countryFilter, setCountryFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiGet<Paginated<Country>>('/countries/')
      .then((c) => setCountries(c.results))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (countryFilter) params.set('country', countryFilter)
    if (categoryFilter) params.set('category', categoryFilter)
    if (riskFilter) params.set('risk_level', riskFilter)
    if (search.trim()) params.set('search', search.trim())
    const qs = params.toString()

    apiGet<Paginated<RegulatoryChange>>(`/regulatory/changes/${qs ? `?${qs}` : ''}`)
      .then((data) => setChanges(data.results))
      .catch(() => setError('Unable to load regulatory changes. Start the backend API.'))
      .finally(() => setLoading(false))
  }, [countryFilter, categoryFilter, riskFilter, search])

  const alertSubscribeLink = useMemo(() => {
    const params = new URLSearchParams()
    const country = countries.find((c) => String(c.id) === countryFilter)
    if (country) params.set('country', country.code)
    if (categoryFilter) params.set('category', categoryFilter)
    const qs = params.toString()
    return `/alerts${qs ? `?${qs}` : ''}`
  }, [countries, countryFilter, categoryFilter])

  return (    <div className="page">
      <header className="page-header">
        <h1>Regulatory Change Engine</h1>
        <p className="lead">Tax, customs, investment, EAC trade, and compliance updates with source-backed impact analysis.</p>
      </header>

      <div className="card filters">
        <label>
          Country
          <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c.code} value={String(c.id)}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>{cat.label}</option>
            ))}
          </select>
        </label>
        <label>
          Risk level
          <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
            {RISK_LEVELS.map((level) => (
              <option key={level.value} value={level.value}>{level.label}</option>
            ))}
          </select>
        </label>
        <label>
          Search
          <input
            type="search"
            placeholder="Tax, customs, EAC…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        {user ? (
          <Link to={alertSubscribeLink} className="filter-action">Subscribe to these alerts</Link>
        ) : (
          <Link to="/login" className="filter-action">Sign in to subscribe</Link>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading…</p>}

      {!loading && changes.length === 0 && !error && (
        <div className="empty-state card">
          <p>No changes match your filters. Run ingestion to populate the feed.</p>
        </div>
      )}

      <div className="list">
        {changes.map((change) => (
          <article key={change.id} className="card list-item">
            <div className="list-item-header">
              <span className="badge">{change.country.code}</span>
              <span className="badge" style={{ background: riskColors[change.risk_level] ?? '#64748b' }}>
                {change.risk_level}
              </span>
              <span className="muted">{change.category}</span>
            </div>
            <h2>{change.title}</h2>
            <p>{change.summary}</p>
            <p><strong>Impact:</strong> {change.business_impact}</p>
            <p><strong>Action:</strong> {change.required_action}</p>
            <div className="card-actions">
              <a href={change.source_url} target="_blank" rel="noreferrer">View source</a>
              <Link
                to={assistantLink(
                  `What are the compliance implications of this regulatory change: ${change.title}?`,
                  change.country.code,
                )}
                className="text-btn"
              >
                Ask assistant
              </Link>
            </div>
          </article>        ))}
      </div>
    </div>
  )
}
