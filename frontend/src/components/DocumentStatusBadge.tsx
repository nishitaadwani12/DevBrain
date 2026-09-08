import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import type { DocumentStatus } from '../lib/types'

const STYLES: Record<DocumentStatus, string> = {
  processing: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  ready: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  failed: 'bg-red-500/10 text-red-300 border-red-500/30',
}

const LABELS: Record<DocumentStatus, string> = {
  processing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
}

export default function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`pill ${STYLES[status]}`}>
      {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
      {status === 'ready' && <CheckCircle2 className="h-3 w-3" />}
      {status === 'failed' && <XCircle className="h-3 w-3" />}
      {LABELS[status]}
    </span>
  )
}
