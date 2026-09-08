import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { authEnabled, isAuthenticated, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [info, setInfo] = useState<string | null>(null)

  // In dev mode (no auth) or when already authenticated, skip the login page.
  if (!authEnabled || isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setBusy(true)
    try {
      if (mode === 'signin') {
        await signIn(email, password)
        navigate('/', { replace: true })
      } else {
        await signUp(email, password)
        setInfo('Account created. Check your email to confirm, then sign in.')
        setMode('signin')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-xl font-bold text-white">
            D
          </div>
          <h1 className="text-2xl font-semibold text-slate-100">DevBrain</h1>
          <p className="mt-1 text-sm text-slate-400">
            Your AI knowledge agent for docs & code.
          </p>
        </div>

        <form className="card flex flex-col gap-4" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Email
            </label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Password
            </label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}
          {info && <p className="text-sm text-emerald-400">{info}</p>}

          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Sign up'}
          </button>

          <button
            type="button"
            className="text-center text-xs text-slate-400 hover:text-slate-200"
            onClick={() => {
              setMode(mode === 'signin' ? 'signup' : 'signin')
              setError(null)
              setInfo(null)
            }}
          >
            {mode === 'signin'
              ? "Don't have an account? Sign up"
              : 'Already have an account? Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
