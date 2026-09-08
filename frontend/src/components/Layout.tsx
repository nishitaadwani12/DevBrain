import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BrainCircuit, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="group flex items-center gap-2.5">
      <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient shadow-glow transition-transform group-hover:scale-105">
        <BrainCircuit className="h-5 w-5 text-white" />
      </span>
      {!compact && (
        <span className="brand-text text-lg font-semibold tracking-tight">
          DevBrain
        </span>
      )}
    </Link>
  )
}

export default function Layout({ children }: { children: ReactNode }) {
  const { authEnabled, session, signOut } = useAuth()

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-white/5 bg-slate-950/60 px-6 backdrop-blur-xl">
        <Brand />

        <div className="flex items-center gap-4">
          <span className="hidden items-center gap-1.5 rounded-full border border-white/5 bg-white/5 px-3 py-1 text-xs text-slate-400 sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {authEnabled ? 'Secure session' : 'Dev mode'}
          </span>
          {authEnabled && session?.user?.email && (
            <span className="hidden text-sm text-slate-400 md:inline">
              {session.user.email}
            </span>
          )}
          {authEnabled && session && (
            <button
              type="button"
              className="btn-ghost px-3 py-1.5 text-xs"
              onClick={() => void signOut()}
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          )}
        </div>
      </header>

      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className="min-h-0 flex-1"
      >
        {children}
      </motion.main>
    </div>
  )
}
