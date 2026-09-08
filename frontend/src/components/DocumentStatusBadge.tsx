import type { DocumentStatus } from '../lib/types'

const STYLES: Record<DocumentStatus, string> = {
  processing: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  ready: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  failed: 'bg-red-500/15 text-red-300 border-red-500/30',
}

const LABELS: Record<DocumentStatus, string> = {
  processing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
}

export default function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STYLES[status]}`}
    >
      {status === 'processing' && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-300" />
      )}
      {LABELS[status]}
    </span>
  )
}
