import { useEffect, useMemo, useState } from 'react'
import { apiGet } from '../lib/api'
import type { Country, CountryRiskSnapshot, EconomicIndicator, Paginated } from '../lib/api'

function riskClass(score: string) {
  const n = Number(score)
  if (n >= 70) return 'risk-good'
  if (n >= 45) return 'risk-mid'
  return 'risk-low'
}

export default function IntelligencePage() {
  const [indicators, setIndicators] = useState<EconomicIndicator[]>([])
  const [risks, setRisks] = useState<CountryRiskSnapshot[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [countryFilter, setCountryFilter] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiGet<Paginated<Country>>('/countries/')
      .then((c) => setCountries(c.results))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const qs = countryFilter ? `?country=${countryFilter}` : ''
    Promise.all([
      apiGet<Paginated<EconomicIndicator>>(`/intelligence/indicators/${qs}`),
      apiGet<Paginated<CountryRiskSnapshot>>(`/intelligence/risk/${qs}`),
    ])
      .then(([ind, risk]) => {
        setIndicators(ind.results)
        setRisks(risk.results)
      })
      .catch(() => setError('Unable to load economic intelligence.'))
      .finally(() => setLoading(false))
  }, [countryFilter])

  const latestRisks = useMemo(() => {
    const byCountry = new Map<string, CountryRiskSnapshot>()
    for (const snap of risks) {
      if (!byCountry.has(snap.country.code)) {
        byCountry.set(snap.country.code, snap)
      }
    }
    return [...byCountry.values()]
  }, [risks])

  return (
    <div className="page">
      <header className="page-header">
        <h1>Economic Intelligence Dashboard</h1>
        <p className="lead">
          World Bank, central bank, FX, and trade data aggregated for EAC market monitoring.
        </p>
      </header>

      <div className="card filters">
        <label>
          Country
          <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
            <option value="">All EAC countries</option>
            {countries.map((c) => (
              <option key={c.code} value={String(c.id)}>{c.name}</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading…</p>}

      {!loading && latestRisks.length > 0 && (
        <section>
          <h2 className="section-title">Country risk snapshots</h2>
          <div className="card-grid">
            {latestRisks.map((snap) => (
              <article key={snap.id} className="card metric">
                <span className="badge">{snap.country.code}</span>
                <h2>{snap.country.name}</h2>
                <p className={`metric-value ${riskClass(snap.overall_score)}`}>
                  {snap.overall_score}
                  <small> overall</small>
                </p>
                <p className="muted">
                  Political {snap.political_risk} · Regulatory {snap.regulatory_risk} · Trade {snap.trade_risk}
                </p>
                {snap.summary && <p>{snap.summary}</p>}
                <p className="muted">As of {snap.as_of}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {!loading && indicators.length === 0 && !error && (
        <div className="empty-state card">
          <p>No indicators for this filter. Run <code>python manage.py ingest --target economic</code>.</p>
        </div>
      )}

      {!loading && indicators.length > 0 && (
        <section>
          <h2 className="section-title">Latest indicators</h2>
          <div className="card-grid">
            {indicators.map((ind) => (
              <article key={ind.id} className="card metric">
                <span className="badge">{ind.country.code}</span>
                <h2>{ind.label}</h2>
                <p className="metric-value">
                  {ind.value} <small>{ind.unit}</small>
                </p>
                <p className="muted">{ind.period}</p>
                {ind.source_url && (
                  <a href={ind.source_url} target="_blank" rel="noreferrer">Source</a>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
