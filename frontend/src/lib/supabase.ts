import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * When VITE_SUPABASE_URL is empty/undefined we run in "dev mode without auth":
 * no Supabase client is created and the app skips login entirely.
 */
export const authEnabled: boolean = Boolean(supabaseUrl && supabaseAnonKey)

export const supabase: SupabaseClient | null = authEnabled
  ? createClient(supabaseUrl as string, supabaseAnonKey as string)
  : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
