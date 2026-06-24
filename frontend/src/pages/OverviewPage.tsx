import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, API_ORIGIN } from '../lib/api'
import type { AlertSubscription, AssistantResponse, HealthStatus, IngestionStatus, Paginated, RegulatoryChange, Vendor } from '../lib/api'
import { useAuth } from '../lib/auth'
import { SITE_MISSION } from '../lib/siteCopy'

const riskColors: Record<string, string> = {
  low: '#16a34a',
  medium: '#ca8a04',
  high: '#ea580c',
  critical: '#dc2626',
}

const quickLinks = [  { to: '/regulatory', label: 'Regulatory feed' },
  { to: '/trade', label: 'Trade procedures' },
  { to: '/assistant', label: 'Ask with evidence' },
  { to: '/vendors', label: 'Vendor diligence' },
]

const pillars = [
  {
    title: 'Regulatory Change Engine',
    description: 'Monitors tax, customs, investment, EAC trade, data protection, and labor updates with source URLs, impact summaries, and required actions.',
    to: '/regulatory',
  },
  {
    title: 'Market Entry Playbooks',
    description: 'Generates registration, tax, import, permit, and compliance checklists tailored to your industry and target country.',
    to: '/playbooks',
  },
  {
    title: 'Vendor Due Diligence',
    description: 'Profiles local suppliers with verification status, risk scores, contract history, and red-flag detection.',
    to: '/vendors',
  },
  {
    title: 'Economic Intelligence',
    description: 'Aggregates World Bank, central bank, FX, and trade data into country risk and market indicators.',
    to: '/intelligence',
  },
  {
    title: 'Proof-Based AI Assistant',
    description: 'Answers only with cited evidence from official notices and trade procedures — never unsupported claims.',
    to: '/assistant',
  },
]

function formatRunDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export default function OverviewPage() {
  const { user, organizationId } = useAuth()
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [orgMetrics, setOrgMetrics] = useState({ vendors: 0, alerts: 0, queries: 0 })
  const [recentChanges, setRecentChanges] = useState<RegulatoryChange[]>([])

  useEffect(() => {
    apiGet<IngestionStatus>('/ingestion/status/')
      .then(setStatus)
      .catch(() => {})
    fetch(`${API_ORIGIN}/api/v1/health/`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {})
    apiGet<Paginated<RegulatoryChange>>('/regulatory/changes/?ordering=-detected_at')
      .then((data) => setRecentChanges(data.results.slice(0, 5)))
      .catch(() => {})
  }, [])
  useEffect(() => {
    if (!user || !organizationId) {
      setOrgMetrics({ vendors: 0, alerts: 0, queries: 0 })
      return
    }
    Promise.all([
      apiGet<Paginated<Vendor>>('/vendors/'),
      apiGet<Paginated<AlertSubscription>>('/regulatory/alerts/'),
      apiGet<Paginated<AssistantResponse>>('/assistant/queries/'),
    ])
      .then(([vendors, alerts, queries]) => {
        setOrgMetrics({
          vendors: vendors.count,
          alerts: alerts.results.filter((a) => a.is_active).length,
          queries: queries.count,
        })
      })
      .catch(() => {})
  }, [user, organizationId])
  return (
    <div className="page">
      <header className="page-header">
        <h1>EastBridge Ops Intelligence</h1>
        <p className="lead">{SITE_MISSION}</p>      </header>

      {status && (
        <>
          <section className="card status-bar">
            <p>
              <span className={`health-dot ${health?.status === 'ok' ? 'ok' : 'warn'}`} />
              API {health?.status ?? 'unknown'} · Database {health?.database ?? 'unknown'}
              {' · '}
              <strong>Embeddings:</strong> {status.embedding_provider} ({status.embedding_model})
            </p>
            <p className="muted">
              Last regulatory sync: {formatRunDate(status.last_regulatory_run?.finished_at)}
              {status.last_regulatory_run?.items_new != null && ` · ${status.last_regulatory_run.items_new} new`}
              {' · '}
              Last economic sync: {formatRunDate(status.last_economic_run?.finished_at)}
            </p>
            <div className="quick-links">
              {quickLinks.map((link) => (
                <Link key={link.to} to={link.to}>{link.label}</Link>
              ))}
            </div>
          </section>

          {user && (
            <section>
              <h2 className="section-title">Your organization</h2>
              <div className="card-grid">
                <Link to="/vendors" className="card metric pillar-link">
                  <h2>Vendors tracked</h2>
                  <p className="metric-value">{orgMetrics.vendors}</p>
                </Link>
                <Link to="/alerts" className="card metric pillar-link">
                  <h2>Active alerts</h2>
                  <p className="metric-value">{orgMetrics.alerts}</p>
                </Link>
                <Link to="/assistant" className="card metric pillar-link">
                  <h2>Saved queries</h2>
                  <p className="metric-value">{orgMetrics.queries}</p>
                </Link>
              </div>
            </section>
          )}

          <section className="card-grid">
            <article className="card metric">
              <h2>Regulatory changes</h2>
              <p className="metric-value">{status.regulatory_changes_count}</p>
            </article>
            <article className="card metric">
              <h2>Indexed evidence</h2>
              <p className="metric-value">{status.evidence_count}</p>
            </article>
            <article className="card metric">
              <h2>Trade procedures</h2>
              <p className="metric-value">{status.trade_procedures_count}</p>
            </article>
            <article className="card metric">
              <h2>Economic indicators</h2>
              <p className="metric-value">{status.economic_indicators_count}</p>
            </article>
          </section>

          {recentChanges.length > 0 && (
            <section>
              <div className="section-header">
                <h2 className="section-title">Latest regulatory changes</h2>
                <Link to="/regulatory">View all</Link>
              </div>
              <div className="list">
                {recentChanges.map((change) => (
                  <article key={change.id} className="card list-item compact">
                    <div className="list-item-header">
                      <span className="badge">{change.country.code}</span>
                      <span className="badge" style={{ background: riskColors[change.risk_level] ?? '#64748b' }}>
                        {change.risk_level}
                      </span>
                      <span className="muted">{new Date(change.detected_at).toLocaleDateString()}</span>
                    </div>
                    <h2>{change.title}</h2>
                    <p>{change.summary}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}
      <section className="card-grid">
        {pillars.map((pillar) => (
          <Link key={pillar.title} to={pillar.to} className="card pillar-link">
            <h2>{pillar.title}</h2>
            <p>{pillar.description}</p>
          </Link>
        ))}
      </section>

      <section className="card highlight">
        <h2>Proof over conversation</h2>
        <p>
          I built EastBridge for teams that need verified sources — current legal changes, trade requirements, country
          risk indicators, tax checklists, vendor diligence, FX movement, and logistics workflows — all with citations
          and change alerts, not unsupported AI claims.
        </p>
      </section>    </div>
  )
}
