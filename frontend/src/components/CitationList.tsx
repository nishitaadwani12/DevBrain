import { useState } from 'react'
import type { Citation } from '../lib/types'

function citationLabel(c: Citation): string {
  // Code citations show path:line, doc citations show filename p.N
  if (c.source_path && (c.start_line != null || c.end_line != null)) {
    const lines =
      c.start_line != null && c.end_line != null && c.end_line !== c.start_line
        ? `${c.start_line}-${c.end_line}`
        : `${c.start_line ?? c.end_line}`
    return `${c.source_path}:${lines}`
  }
  if (c.page != null) {
    return `${c.filename} p.${c.page}`
  }
  return c.filename
}

function CitationItem({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false)
  return (
    <li className="rounded-lg border border-slate-800 bg-slate-900/60">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600/20 text-[11px] font-semibold text-indigo-300">
          {citation.index}
        </span>
        <span className="truncate font-mono text-xs text-slate-300">
          {citationLabel(citation)}
        </span>
        <span className="ml-auto text-xs text-slate-500">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <pre className="mx-3 mb-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-2 text-[11px] text-slate-400">
          {citation.content}
        </pre>
      )}
    </li>
  )
}

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Sources
      </p>
      <ul className="space-y-1.5">
        {citations.map((c) => (
          <CitationItem key={`${c.chunk_id}-${c.index}`} citation={c} />
        ))}
      </ul>
    </div>
  )
}
