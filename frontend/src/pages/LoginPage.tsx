import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import './LoginPage.css'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const isDev = import.meta.env.DEV

  useEffect(() => {
    if (user) navigate('/')
  }, [user, navigate])

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData(e.currentTarget)
    try {
      await login(String(form.get('username')), String(form.get('password')))
      navigate('/')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Sign in</h1>
        <p className="muted">Access organization-scoped vendors and playbooks.</p>
        <label>
          Username
          <input name="username" defaultValue={isDev ? 'demo' : ''} required autoComplete="username" />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            defaultValue={isDev ? 'demo12345' : ''}
            required
            autoComplete="current-password"
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        {isDev && <p className="hint muted">Local dev: demo / demo12345</p>}
      </form>
    </div>
  )
}
