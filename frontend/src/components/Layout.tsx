import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout({ children }: { children: ReactNode }) {
  const { authEnabled, session, signOut } = useAuth()

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-900/60 px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            D
          </span>
          <span className="text-lg font-semibold tracking-tight text-slate-100">
            DevBrain
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {authEnabled && session?.user?.email && (
            <span className="text-sm text-slate-400">{session.user.email}</span>
          )}
          {authEnabled && session && (
            <button
              type="button"
              className="btn-ghost px-3 py-1.5 text-xs"
              onClick={() => void signOut()}
            >
              Sign out
            </button>
          )}
        </div>
      </header>

      <main className="min-h-0 flex-1">{children}</main>
    </div>
  )
}
