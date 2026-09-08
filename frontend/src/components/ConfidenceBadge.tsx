import type { Confidence } from '../lib/types'

const STYLES: Record<Confidence['label'], string> = {
  high: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  medium: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  low: 'bg-red-500/15 text-red-300 border-red-500/30',
  none: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
}

export default function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
          STYLES[confidence.label]
        }`}
        title={`Confidence score: ${confidence.score.toFixed(2)}`}
      >
        {confidence.label} confidence
      </span>
      {!confidence.grounded && (
        <span className="text-[11px] text-amber-400">
          ⚠ weakly grounded — verify against sources
        </span>
      )}
    </div>
  )
}
