import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../lib/api'
import type { Country, Paginated, TradeProcedure } from '../lib/api'
import { assistantLink } from '../lib/assistantLink'
import { exportTradeProcedureMarkdown } from '../lib/exportTradeProcedure'

const ACTIVITY_TYPES = [
  { value: '', label: 'All activities' },
  { value: 'import', label: 'Import' },
  { value: 'export', label: 'Export' },
  { value: 'transit', label: 'Transit' },
  { value: 'registration', label: 'Business registration' },
  { value: 'licensing', label: 'Licensing' },
  { value: 'customs', label: 'Customs clearance' },
  { value: 'other', label: 'Other' },
]

export default function TradePage() {
  const [procedures, setProcedures] = useState<TradeProcedure[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [countryFilter, setCountryFilter] = useState('')
  const [activityFilter, setActivityFilter] = useState('')
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
    if (activityFilter) params.set('activity_type', activityFilter)
    if (search.trim()) params.set('search', search.trim())
    const qs = params.toString()

    apiGet<Paginated<TradeProcedure>>(`/trade/procedures/${qs ? `?${qs}` : ''}`)
      .then((data) => setProcedures(data.results))
      .catch(() => setError('Unable to load trade procedures. Run sync_trade_procedures on the backend.'))
      .finally(() => setLoading(false))
  }, [countryFilter, activityFilter, search])

  return (
    <div className="page">
      <header className="page-header">
        <h1>EAC Trade Procedures</h1>
        <p className="lead">
          Structured import, export, and clearance procedures from EAC Trade Information Portals.
        </p>
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
          Activity
          <select value={activityFilter} onChange={(e) => setActivityFilter(e.target.value)}>
            {ACTIVITY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
        <label>
          Search
          <input
            type="search"
            placeholder="Import, customs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading…</p>}

      {!loading && procedures.length === 0 && !error && (
        <div className="empty-state card">
          <p>No procedures match your filters. Run `python manage.py sync_trade_procedures --offline`.</p>
        </div>
      )}

      <div className="list">
        {procedures.map((proc) => (
          <article key={proc.id} className="card list-item">
            <div className="list-item-header">
              <span className="badge">{proc.country.code}</span>
              <span className="badge">{proc.activity_type}</span>
              <span className="muted">{proc.source_portal}</span>
            </div>
            <h2>{proc.title}</h2>
            <p>{proc.summary}</p>
            {proc.estimated_days && (
              <p className="muted">Estimated: {proc.estimated_days} days {proc.estimated_cost && `· ${proc.estimated_cost}`}</p>
            )}
            <ol className="steps">
              {proc.steps.map((step) => (
                <li key={step.id}>
                  <strong>{step.title}</strong>
                  {step.responsible_agency && <span className="badge">{step.responsible_agency}</span>}
                  <p>{step.description}</p>
                  {step.documents_required.length > 0 && (
                    <ul>
                      {step.documents_required.map((doc) => (
                        <li key={doc}>{doc}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
            <div className="card-actions">
              <a href={proc.source_url} target="_blank" rel="noreferrer">Official source</a>
              <button type="button" className="text-btn" onClick={() => exportTradeProcedureMarkdown(proc)}>
                Export Markdown
              </button>
              <Link
                to={assistantLink(
                  `What are the requirements and steps for: ${proc.title}?`,
                  proc.country.code,
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
