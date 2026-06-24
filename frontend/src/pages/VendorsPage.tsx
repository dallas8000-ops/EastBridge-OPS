import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiPostForm,
  mediaUrl,
} from '../lib/api'
import type { Country, Paginated, Vendor } from '../lib/api'
import { useAuth } from '../lib/auth'

const DOCUMENT_TYPES = [
  'certificate_of_incorporation',
  'tax_clearance',
  'bank_reference',
  'contract',
  'other',
]

const VERIFICATION_STATUSES = ['pending', 'in_review', 'verified', 'rejected', 'flagged']

function VendorCard({
  vendor,
  countries,
  onUpdated,
}: {
  vendor: Vendor
  countries: Country[]
  onUpdated: () => void
}) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [actionError, setActionError] = useState('')

  async function handleUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setUploading(true)
    setUploadError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPostForm(`/vendors/${vendor.id}/upload_document/`, form)
      e.currentTarget.reset()
      onUpdated()
    } catch {
      setUploadError('Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  async function handleEdit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setSaving(true)
    setActionError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPatch<Vendor>(`/vendors/${vendor.id}/`, {
        name: form.get('name'),
        registration_number: form.get('registration_number'),
        country_code: form.get('country_code'),
        business_profile: form.get('business_profile'),
        verification_status: form.get('verification_status'),
        risk_score: form.get('risk_score'),
      })
      setEditing(false)
      onUpdated()
    } catch {
      setActionError('Update failed.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Remove ${vendor.name}?`)) return
    setActionError('')
    try {
      await apiDelete(`/vendors/${vendor.id}/`)
      onUpdated()
    } catch {
      setActionError('Delete failed.')
    }
  }

  async function handleAddContract(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setActionError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPost(`/vendors/${vendor.id}/add_contract/`, {
        contract_ref: form.get('contract_ref'),
        value_usd: form.get('value_usd') || null,
        start_date: form.get('start_date') || null,
        end_date: form.get('end_date') || null,
        notes: form.get('notes'),
      })
      e.currentTarget.reset()
      onUpdated()
    } catch {
      setActionError('Failed to add contract.')
    }
  }

  async function handleAddPayment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setActionError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPost(`/vendors/${vendor.id}/add_payment/`, {
        amount_usd: form.get('amount_usd'),
        payment_date: form.get('payment_date'),
        status: form.get('status') || 'completed',
        notes: form.get('notes'),
      })
      e.currentTarget.reset()
      onUpdated()
    } catch {
      setActionError('Failed to add payment.')
    }
  }

  return (
    <article className="card vendor-card">
      <div className="list-item-header">
        <span className="badge">{vendor.country.code}</span>
        <span className="badge">{vendor.verification_status}</span>
        <div className="vendor-actions">
          <button type="button" className="text-btn" onClick={() => setEditing(!editing)}>
            {editing ? 'Cancel' : 'Edit'}
          </button>
          <button type="button" className="text-btn danger" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      {editing ? (
        <form className="form vendor-edit" onSubmit={handleEdit}>
          <label>
            Name
            <input name="name" required defaultValue={vendor.name} />
          </label>
          <label>
            Registration number
            <input name="registration_number" defaultValue={vendor.registration_number} />
          </label>
          <label>
            Country
            <select name="country_code" defaultValue={vendor.country.code}>
              {countries.map((c) => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </label>
          <label>
            Verification
            <select name="verification_status" defaultValue={vendor.verification_status}>
              {VERIFICATION_STATUSES.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </label>
          <label>
            Business profile
            <textarea name="business_profile" rows={2} defaultValue={vendor.business_profile ?? ''} />
          </label>
          <label>
            Risk score
            <input name="risk_score" type="number" min="0" max="100" defaultValue={vendor.risk_score} />
          </label>
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
        </form>
      ) : (
        <>
          <h2>{vendor.name}</h2>
          <p className="muted">Reg: {vendor.registration_number || '—'}</p>
          <p>Risk score: <strong>{vendor.risk_score}</strong></p>
          {vendor.red_flags.length > 0 && (
            <ul>
              {vendor.red_flags.map((flag) => (
                <li key={flag} className="flag">{flag}</li>
              ))}
            </ul>
          )}
        </>
      )}

      <section className="vendor-docs">
        <h3>Documents ({vendor.documents.length})</h3>
        {vendor.documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <ul className="doc-list">
            {vendor.documents.map((doc) => (
              <li key={doc.id}>
                <a href={mediaUrl(doc.file)} target="_blank" rel="noreferrer">
                  {doc.document_type.replace(/_/g, ' ')}
                </a>
                {doc.verified && <span className="badge">verified</span>}
                <span className="muted"> · {new Date(doc.uploaded_at).toLocaleDateString()}</span>
              </li>
            ))}
          </ul>
        )}

        <form className="doc-upload" onSubmit={handleUpload}>
          <select name="document_type" required defaultValue="certificate_of_incorporation">
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input name="file" type="file" required accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" />
          <button type="submit" disabled={uploading}>
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </form>
        {uploadError && <p className="error">{uploadError}</p>}
      </section>

      <section className="vendor-docs">
        <h3>Contracts ({vendor.contracts?.length ?? 0})</h3>
        {(vendor.contracts?.length ?? 0) === 0 ? (
          <p className="muted">No contracts recorded.</p>
        ) : (
          <ul className="doc-list">
            {vendor.contracts.map((c) => (
              <li key={c.id}>
                <strong>{c.contract_ref}</strong>
                {c.value_usd && <span className="muted"> · ${c.value_usd}</span>}
                {(c.start_date || c.end_date) && (
                  <span className="muted"> · {c.start_date ?? '?'} → {c.end_date ?? '?'}</span>
                )}
                {c.notes && <p className="muted">{c.notes}</p>}
              </li>
            ))}
          </ul>
        )}
        <form className="mini-form" onSubmit={handleAddContract}>
          <input name="contract_ref" placeholder="Contract ref" required />
          <input name="value_usd" type="number" step="0.01" placeholder="Value USD" />
          <input name="start_date" type="date" />
          <input name="end_date" type="date" />
          <input name="notes" placeholder="Notes" />
          <button type="submit">Add contract</button>
        </form>
      </section>

      <section className="vendor-docs">
        <h3>Payments ({vendor.payments?.length ?? 0})</h3>
        {(vendor.payments?.length ?? 0) === 0 ? (
          <p className="muted">No payment history.</p>
        ) : (
          <ul className="doc-list">
            {vendor.payments.map((p) => (
              <li key={p.id}>
                <strong>${p.amount_usd}</strong>
                <span className="muted"> · {p.payment_date} · {p.status}</span>
                {p.notes && <span className="muted"> — {p.notes}</span>}
              </li>
            ))}
          </ul>
        )}
        <form className="mini-form" onSubmit={handleAddPayment}>
          <input name="amount_usd" type="number" step="0.01" placeholder="Amount USD" required />
          <input name="payment_date" type="date" required />
          <select name="status" defaultValue="completed">
            <option value="completed">completed</option>
            <option value="pending">pending</option>
            <option value="late">late</option>
          </select>
          <input name="notes" placeholder="Notes" />
          <button type="submit">Add payment</button>
        </form>
      </section>

      {actionError && <p className="error">{actionError}</p>}
    </article>
  )
}

export default function VendorsPage() {
  const { user } = useAuth()
  const [vendors, setVendors] = useState<Vendor[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)

  function loadVendors() {
    apiGet<Paginated<Vendor>>('/vendors/')
      .then((data) => setVendors(data.results))
      .catch(() => setError('Unable to load vendors.'))
  }

  useEffect(() => {
    if (!user) return
    loadVendors()
    apiGet<Paginated<Country>>('/countries/').then((c) => setCountries(c.results)).catch(() => {})
  }, [user])

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    try {
      await apiPost<Vendor>('/vendors/', {
        name: form.get('name'),
        registration_number: form.get('registration_number'),
        country_code: form.get('country_code'),
        business_profile: form.get('business_profile'),
        risk_score: form.get('risk_score') || '50',
      })
      setShowForm(false)
      loadVendors()
    } catch {
      setError('Failed to add vendor.')
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="page">
        <header className="page-header">
          <h1>Vendor Due Diligence</h1>
        </header>
        <div className="card">
          <p>Vendor due diligence is organization-scoped. <Link to="/login">Sign in</Link> to view your suppliers.</p>
        </div>
      </div>
    )
  }

  const avgRisk = vendors.length
    ? (vendors.reduce((sum, v) => sum + Number(v.risk_score), 0) / vendors.length).toFixed(1)
    : '—'
  const flagged = vendors.filter((v) => v.red_flags.length > 0 || v.verification_status === 'flagged').length

  return (
    <div className="page">
      <header className="page-header">
        <h1>Vendor Due Diligence</h1>
        <p className="lead">Local supplier profiles with verification status, risk scores, and document uploads.</p>
      </header>

      {vendors.length > 0 && (
        <section className="card-grid vendor-summary">
          <article className="card metric">
            <h2>Suppliers</h2>
            <p className="metric-value">{vendors.length}</p>
          </article>
          <article className="card metric">
            <h2>Avg risk score</h2>
            <p className="metric-value">{avgRisk}</p>
          </article>
          <article className="card metric">
            <h2>Flagged / red flags</h2>
            <p className="metric-value">{flagged}</p>
          </article>
        </section>
      )}

      <button type="button" className="card" style={{ cursor: 'pointer', textAlign: 'left' }} onClick={() => setShowForm(!showForm)}>
        {showForm ? '− Cancel' : '+ Add vendor'}
      </button>

      {showForm && (
        <form className="card form" onSubmit={handleCreate}>
          <label>
            Name
            <input name="name" required />
          </label>
          <label>
            Registration number
            <input name="registration_number" />
          </label>
          <label>
            Country
            <select name="country_code" required defaultValue="UG">
              {countries.map((c) => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </label>
          <label>
            Business profile
            <textarea name="business_profile" rows={2} />
          </label>
          <label>
            Risk score (0–100)
            <input name="risk_score" type="number" min="0" max="100" defaultValue="50" />
          </label>
          <button type="submit" disabled={loading}>{loading ? 'Saving…' : 'Save vendor'}</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {vendors.length === 0 && !error && (
        <div className="empty-state card">
          <p>No vendors on file for your organization. Add a supplier above.</p>
        </div>
      )}

      <div className="card-grid">
        {vendors.map((vendor) => (
          <VendorCard
            key={vendor.id}
            vendor={vendor}
            countries={countries}
            onUpdated={loadVendors}
          />
        ))}
      </div>
    </div>
  )
}
