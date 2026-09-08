import { ShieldCheck, TriangleAlert } from 'lucide-react'
import type { Confidence } from '../lib/types'

const STYLES: Record<Confidence['label'], string> = {
  high: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  medium: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  low: 'bg-red-500/10 text-red-300 border-red-500/30',
  none: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
}

export default function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span
        className={`pill ${STYLES[confidence.label]}`}
        title={`Confidence score: ${confidence.score.toFixed(2)}`}
      >
        <ShieldCheck className="h-3 w-3" />
        {confidence.label} confidence
      </span>
      {!confidence.grounded && (
        <span className="inline-flex items-center gap-1 text-[11px] text-amber-400">
          <TriangleAlert className="h-3 w-3" />
          weakly grounded — verify against sources
        </span>
      )}
    </div>
  )
}
