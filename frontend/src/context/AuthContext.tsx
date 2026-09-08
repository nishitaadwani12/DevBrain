import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Session } from '@supabase/supabase-js'
import { authEnabled, supabase } from '../lib/supabase'

interface AuthContextValue {
  authEnabled: boolean
  session: Session | null
  loading: boolean
  /** True when the user can access protected routes. */
  isAuthenticated: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState<boolean>(authEnabled)

  useEffect(() => {
    if (!supabase) {
      setLoading(false)
      return
    }

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
    })

    return () => sub.subscription.unsubscribe()
  }, [])

  const value = useMemo<AuthContextValue>(() => {
    const signIn = async (email: string, password: string) => {
      if (!supabase) return
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
    }

    const signUp = async (email: string, password: string) => {
      if (!supabase) return
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) throw error
    }

    const signOut = async () => {
      if (!supabase) return
      await supabase.auth.signOut()
    }

    return {
      authEnabled,
      session,
      loading,
      isAuthenticated: !authEnabled || Boolean(session),
      signIn,
      signUp,
      signOut,
    }
  }, [session, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
