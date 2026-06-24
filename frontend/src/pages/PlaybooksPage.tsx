import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
} from '../lib/api'
import type { Country, Paginated, Playbook, PlaybookStep } from '../lib/api'
import { useAuth } from '../lib/auth'
import { exportPlaybookMarkdown } from '../lib/exportPlaybook'

interface Industry {
  id: number
  slug: string
  name: string
}

function PlaybookView({
  playbook,
  onStepToggle,
}: {
  playbook: Playbook
  onStepToggle: (stepId: number, completed: boolean) => void
}) {
  const completed = playbook.steps.filter((s) => s.is_completed).length
  const total = playbook.steps.length
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <section className="card">
      <div className="playbook-toolbar">
        <h2>
          {playbook.origin_country} → {playbook.target_country.name} ({playbook.industry.name})
        </h2>
        <button type="button" className="text-btn" onClick={() => exportPlaybookMarkdown(playbook)}>
          Export Markdown
        </button>
      </div>
      {playbook.estimated_timeline_weeks && (
        <p className="muted">Estimated setup: {playbook.estimated_timeline_weeks} weeks</p>
      )}
      <p className="progress-label">
        Progress: <strong>{completed}/{total}</strong> steps ({progress}%)
      </p>
      <div className="progress-bar" aria-hidden>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <ol className="steps checklist">
        {playbook.steps.map((step) => (
          <li key={step.id} className={step.is_completed ? 'step-done' : ''}>
            <label className="step-check">
              <input
                type="checkbox"
                checked={step.is_completed}
                onChange={(e) => onStepToggle(step.id, e.target.checked)}
              />
              <strong>{step.title}</strong>
            </label>
            <span className="badge">{step.step_type}</span>
            <p>{step.description}</p>
            {step.source_url && (
              <p className="muted">
                <a href={step.source_url} target="_blank" rel="noreferrer">Source</a>
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}

function updatePlaybookStep(playbook: Playbook, stepId: number, patch: Partial<PlaybookStep>): Playbook {
  return {
    ...playbook,
    steps: playbook.steps.map((s) => (s.id === stepId ? { ...s, ...patch } : s)),
  }
}

export default function PlaybooksPage() {
  const { user } = useAuth()
  const [countries, setCountries] = useState<Country[]>([])
  const [industries, setIndustries] = useState<Industry[]>([])
  const [saved, setSaved] = useState<Playbook[]>([])
  const [playbook, setPlaybook] = useState<Playbook | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiGet<Paginated<Country>>('/countries/')
      .then((c) => setCountries(c.results))
      .catch(() => setError('Unable to load form options.'))
    apiGet<Paginated<Industry>>('/playbooks/industries/')
      .then((i) => setIndustries(i.results))
      .catch(() => setError('Unable to load form options.'))
  }, [])

  useEffect(() => {
    if (!user) return
    apiGet<Paginated<Playbook>>('/playbooks/')
      .then((data) => {
        setSaved(data.results)
        if (data.results.length > 0 && !playbook) {
          setPlaybook(data.results[0])
        }
      })
      .catch(() => {})
  }, [user])

  async function handleStepToggle(stepId: number, completed: boolean) {
    if (!playbook) return
    setPlaybook(updatePlaybookStep(playbook, stepId, { is_completed: completed }))
    setSaved((prev) =>
      prev.map((p) => (p.id === playbook.id ? updatePlaybookStep(p, stepId, { is_completed: completed }) : p)),
    )
    try {
      await apiPatch<PlaybookStep>(`/playbooks/steps/${stepId}/`, { is_completed: completed })
    } catch {
      setPlaybook(updatePlaybookStep(playbook, stepId, { is_completed: !completed }))
      setError('Failed to update step.')
    }
  }

  async function handleDeletePlaybook() {
    if (!playbook) return
    if (!globalThis.confirm('Delete this playbook? This cannot be undone.')) return
    try {
      await apiDelete(`/playbooks/${playbook.id}/`)
      const remaining = saved.filter((p) => p.id !== playbook.id)
      setSaved(remaining)
      setPlaybook(remaining[0] ?? null)
      setError('')
    } catch {
      setError('Failed to delete playbook.')
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    try {
      const result = await apiPost<Playbook>('/playbooks/generate/', {
        origin_country: form.get('origin_country'),
        target_country_code: form.get('target_country'),
        industry_slug: form.get('industry'),
        company_description: form.get('description'),
      })
      setPlaybook(result)
      setSaved((prev) => [result, ...prev.filter((p) => p.id !== result.id)])
    } catch {
      setError('Failed to generate playbook. Sign in and ensure your organization is selected.')
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="page">
        <header className="page-header">
          <h1>Market Entry Playbooks</h1>
        </header>
        <div className="card">
          <p>
            Playbooks are saved to your organization. <Link to="/login">Sign in</Link> to generate
            and view market entry checklists.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Market Entry Playbooks</h1>
        <p className="lead">
          Example: &ldquo;I am a German solar equipment company entering Uganda.&rdquo;
        </p>
      </header>

      {saved.length > 0 && (
        <div className="card">
          <label className="saved-picker">
            Saved playbooks
            <select
              value={playbook?.id ?? ''}
              onChange={(e) => {
                const selected = saved.find((p) => p.id === Number(e.target.value))
                if (selected) setPlaybook(selected)
              }}
            >
              {saved.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.origin_country} → {p.target_country.name} ({p.industry.name})
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Origin country (ISO code)
          <input name="origin_country" defaultValue="DE" required maxLength={2} />
        </label>
        <label>
          Target country
          <select name="target_country" required defaultValue="UG">
            {countries.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>
          Industry
          <select name="industry" required defaultValue="solar-equipment">
            {industries.map((i) => (
              <option key={i.slug} value={i.slug}>{i.name}</option>
            ))}
          </select>
        </label>
        <label>
          Company description
          <textarea name="description" rows={3} placeholder="German solar equipment manufacturer..." />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Generating…' : 'Generate playbook'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {playbook && (
        <>
          <div className="card-actions" style={{ marginBottom: '0.75rem' }}>
            <button type="button" className="text-btn danger" onClick={handleDeletePlaybook}>
              Delete playbook
            </button>
          </div>
          <PlaybookView playbook={playbook} onStepToggle={handleStepToggle} />
        </>
      )}    </div>
  )
}
