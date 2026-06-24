export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'
export const API_ORIGIN =
  import.meta.env.VITE_API_ORIGIN ??
  (API_BASE.startsWith('http') ? API_BASE.replace(/\/api\/v1\/?$/, '') : '')

export function mediaUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_ORIGIN}${path.startsWith('/') ? path : `/${path}`}`
}

function getAuthHeaders(json = true): Record<string, string> {
  const headers: Record<string, string> = {}
  if (json) headers['Content-Type'] = 'application/json'
  const token = localStorage.getItem('eastbridge_access')
  const org = localStorage.getItem('eastbridge_org')
  if (token) headers.Authorization = `Bearer ${token}`
  if (org) headers['X-Organization-ID'] = org
  return headers
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: getAuthHeaders() })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function apiPostForm<T>(path: string, body: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: getAuthHeaders(false),
    body,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Country {
  id: number
  code: string
  name: string
  is_eac_member: boolean
  currency_code: string
}

export interface RegulatoryChange {
  id: number
  title: string
  summary: string
  business_impact: string
  required_action: string
  category: string
  risk_level: string
  source_url: string
  country: Country
  published_at: string | null
  detected_at: string
}

export interface PlaybookStep {
  id: number
  step_type: string
  title: string
  description: string
  source_url: string
  sort_order: number
  is_completed: boolean
}

export interface Playbook {
  id: number
  origin_country: string
  industry: { id: number; slug: string; name: string }
  target_country: Country
  company_description: string
  estimated_timeline_weeks: number | null
  generated_at: string
  steps: PlaybookStep[]
}

export interface VendorDocument {
  id: number
  document_type: string
  file: string
  uploaded_at: string
  verified: boolean
}

export interface VendorContract {
  id: number
  contract_ref: string
  value_usd: string | null
  start_date: string | null
  end_date: string | null
  notes: string
}

export interface VendorPayment {
  id: number
  amount_usd: string
  payment_date: string
  status: string
  notes: string
}

export interface Vendor {
  id: number
  name: string
  registration_number: string
  country: Country
  business_profile?: string
  verification_status: string
  risk_score: string
  red_flags: string[]
  documents: VendorDocument[]
  contracts: VendorContract[]
  payments: VendorPayment[]
}

export interface HealthStatus {
  status: string
  database: string
}

export interface EconomicIndicator {
  id: number
  country: Country
  indicator_type: string
  label: string
  value: string
  unit: string
  period: string
  source_url: string
}

export interface TradeProcedureStep {
  id: number
  sort_order: number
  title: string
  description: string
  responsible_agency: string
  documents_required: string[]
  estimated_days: number | null
}

export interface TradeProcedure {
  id: number
  external_id: string
  title: string
  slug: string
  country: Country
  activity_type: string
  summary: string
  source_url: string
  source_portal: string
  estimated_days: number | null
  estimated_cost: string
  last_synced_at: string
  steps: TradeProcedureStep[]
}

export interface Citation {
  id: number
  evidence: { id: number; title: string; source_url: string; published_at: string | null }
  excerpt: string
  relevance_score: string | null
}

export interface AssistantResponse {
  id: number
  question: string
  answer: string
  has_sufficient_evidence: boolean
  refusal_reason: string
  retrieval_method: string
  citations: Citation[]
  created_at: string
}

export interface IngestionStatus {
  evidence_count: number
  regulatory_changes_count: number
  economic_indicators_count: number
  trade_procedures_count: number
  embedding_provider: string
  embedding_model: string
  last_regulatory_run: { finished_at: string | null; items_new: number } | null
  last_economic_run: { finished_at: string | null; items_new: number } | null
}

export interface CountryRiskSnapshot {
  id: number
  country: Country
  overall_score: string
  political_risk: string
  regulatory_risk: string
  trade_risk: string
  summary: string
  as_of: string
}

export interface AlertSubscription {
  id: number
  email: string
  country: Country | null
  category: string
  is_active: boolean
  created_at: string
}
