import type { ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export function ErrorState({
  message,
  onRetry,
  compact = false,
}: {
  message: string
  onRetry?: () => void
  compact?: boolean
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 rounded-2xl border border-red-500/20 bg-red-500/5 text-center ${
        compact ? 'p-4' : 'p-8'
      }`}
    >
      <AlertCircle className="h-6 w-6 text-red-400" />
      <p className="text-sm text-red-200">{message}</p>
      {onRetry && (
        <button type="button" className="btn-secondary" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-10 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 text-indigo-300">
        {icon}
      </div>
      <div>
        <p className="text-base font-medium text-slate-100">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-400">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
