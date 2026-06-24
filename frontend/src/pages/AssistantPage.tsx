import { FormEvent, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiGet, apiPost } from '../lib/api'
import type { AssistantResponse, Paginated } from '../lib/api'
import { useAuth } from '../lib/auth'
import { assistantToMarkdown, copyAssistantMarkdown, exportAssistantMarkdown } from '../lib/exportAssistant'

function QueryResult({ response }: { response: AssistantResponse }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await copyAssistantMarkdown(response)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <section className="card">
      <div className="card-actions">
        {response.has_sufficient_evidence && (
          <>
            <button type="button" className="text-btn" onClick={() => exportAssistantMarkdown(response)}>
              Download Markdown
            </button>
            <button type="button" className="text-btn" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy answer'}
            </button>
          </>
        )}
      </div>
      {response.retrieval_method && (
        <p className="muted">
          Retrieval: <span className="badge">{response.retrieval_method}</span>
        </p>
      )}
      {!response.has_sufficient_evidence ? (
        <div className="refusal">
          <h2>Insufficient evidence</h2>
          <p>{response.refusal_reason}</p>
        </div>
      ) : (
        <>
          <h2>Answer</h2>
          <p>{response.answer}</p>
          <h3>Citations</h3>
          <ul className="citations">
            {response.citations.map((c) => (
              <li key={c.id}>
                <a href={c.evidence.source_url} target="_blank" rel="noreferrer">
                  {c.evidence.title}
                </a>
                <blockquote>{c.excerpt}</blockquote>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

const SAMPLE_QUESTIONS = [
  { country: 'UG', text: 'What are the import duty requirements for solar panels in Uganda?' },
  { country: 'KE', text: 'What are the EAC customs procedures for importing machinery to Kenya?' },
  { country: 'TZ', text: 'What tax registration steps apply to foreign companies in Tanzania?' },
  { country: 'RW', text: 'What trade procedures apply to commercial imports in Rwanda?' },
]

export default function AssistantPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [response, setResponse] = useState<AssistantResponse | null>(null)
  const [history, setHistory] = useState<AssistantResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [countryCode, setCountryCode] = useState(searchParams.get('country') ?? '')
  const [question, setQuestion] = useState(searchParams.get('q') ?? '')

  useEffect(() => {
    const q = searchParams.get('q')
    const country = searchParams.get('country')
    if (q) setQuestion(q)
    if (country) setCountryCode(country.toUpperCase())
  }, [searchParams])
  useEffect(() => {
    if (!user) return
    apiGet<Paginated<AssistantResponse>>('/assistant/queries/')
      .then((data) => setHistory(data.results))
      .catch(() => {})
  }, [user])

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const result = await apiPost<AssistantResponse>('/assistant/queries/ask/', {
        question,
        country_code: countryCode,
      })
      setResponse(result)
      if (user) {
        setHistory((prev) => [result, ...prev.filter((q) => q.id !== result.id)])
      }
    } catch {
      setError('Assistant request failed. Check that the API is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Proof-Based AI Assistant</h1>
        <p className="lead">
          Every answer is tied to source evidence. No citations, no answer.
        </p>
      </header>

      <div className={user && history.length > 0 ? 'assistant-layout' : ''}>
        {user && history.length > 0 && (
          <aside className="card history-panel">
            <h2>Recent queries</h2>
            <ul className="history-list">
              {history.map((q) => (
                <li key={q.id}>
                  <button
                    type="button"
                    className={`history-item${response?.id === q.id ? ' active' : ''}`}
                    onClick={() => setResponse(q)}
                  >
                    <span className="history-q">{q.question}</span>
                    <span className="muted">
                      {new Date(q.created_at).toLocaleString()}
                      {q.has_sufficient_evidence ? '' : ' · refused'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}

        <div className="assistant-main">
          <div className="card sample-prompts">
            <p className="muted">Example questions</p>
            <div className="chip-row">
              {SAMPLE_QUESTIONS.map((sample) => (
                <button
                  key={sample.country}
                  type="button"
                  className="chip"
                  onClick={() => {
                    setCountryCode(sample.country)
                    setQuestion(sample.text)
                  }}
                >
                  {sample.country}
                </button>
              ))}
            </div>
          </div>

          <form className="card form" onSubmit={handleSubmit}>
            <label>
              Country (optional)
              <input
                name="country_code"
                maxLength={2}
                placeholder="UG"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
              />
            </label>
            <label>
              Question
              <textarea
                name="question"
                rows={4}
                required
                placeholder="What are the import duty requirements for solar panels in Uganda?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? 'Searching evidence…' : 'Ask with evidence'}
            </button>
          </form>

          {!user && (
            <p className="muted card">
              <Link to="/login">Sign in</Link> to save query history to your organization.
            </p>
          )}

          {error && <p className="error">{error}</p>}

          {response && <QueryResult response={response} />}
        </div>
      </div>
    </div>
  )
}
