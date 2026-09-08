import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, FileText, Quote } from 'lucide-react'
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
    <li className="overflow-hidden rounded-xl border border-white/5 bg-slate-950/40">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-white/5"
      >
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500/30 to-violet-500/30 text-[11px] font-semibold text-indigo-200">
          {citation.index}
        </span>
        <FileText className="h-3.5 w-3.5 shrink-0 text-slate-500" />
        <span className="truncate font-mono text-xs text-slate-300">
          {citationLabel(citation)}
        </span>
        <ChevronDown
          className={`ml-auto h-3.5 w-3.5 shrink-0 text-slate-500 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
          >
            <pre className="mx-3 mb-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-white/5 bg-black/40 p-2.5 text-[11px] leading-relaxed text-slate-400">
              {citation.content}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  )
}

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Quote className="h-3 w-3" />
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
