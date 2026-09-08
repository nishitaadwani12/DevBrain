import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { FileCode, GitBranch, Layers } from 'lucide-react'
import { getRepoGraph } from '../lib/api'
import type { RepoGraph } from '../lib/types'
import { Skeleton } from './ui/Skeleton'
import { ErrorState } from './ui/States'

const LANGUAGE_COLORS = [
  '#818cf8', // indigo
  '#34d399', // emerald
  '#fbbf24', // amber
  '#f472b6', // pink
  '#22d3ee', // cyan
  '#c084fc', // purple
  '#f87171', // red
  '#2dd4bf', // teal
  '#facc15', // yellow
  '#60a5fa', // blue
]

function colorForLanguage(language: string, languages: string[]): string {
  const idx = languages.indexOf(language)
  if (idx === -1) return '#64748b'
  return LANGUAGE_COLORS[idx % LANGUAGE_COLORS.length]
}

function buildFlow(graph: RepoGraph): { nodes: Node[]; edges: Edge[] } {
  const languages = graph.stats.languages ?? []
  const count = graph.nodes.length
  const cols = Math.max(1, Math.ceil(Math.sqrt(count)))
  const gapX = 210
  const gapY = 92

  const nodes: Node[] = graph.nodes.map((n, i) => {
    const color = colorForLanguage(n.language, languages)
    return {
      id: n.id,
      position: { x: (i % cols) * gapX, y: Math.floor(i / cols) * gapY },
      data: { label: n.label },
      style: {
        background: 'rgba(15,23,42,0.85)',
        border: `1px solid ${color}55`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 12,
        color: '#e2e8f0',
        fontSize: 11,
        fontFamily: 'ui-monospace, monospace',
        padding: '8px 12px',
        width: 170,
        boxShadow: '0 8px 24px -12px rgba(0,0,0,0.6)',
      },
    }
  })

  const nodeIds = new Set(graph.nodes.map((n) => n.id))
  const edges: Edge[] = graph.edges
    .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map((e, i) => ({
      id: `e-${e.source}-${e.target}-${i}`,
      source: e.source,
      target: e.target,
      style: { stroke: 'rgba(148,163,184,0.25)' },
    }))

  return { nodes, edges }
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: number
  label: string
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/5 px-3 py-2">
      <span className="text-indigo-300">{icon}</span>
      <span>
        <span className="block text-base font-semibold text-slate-100">{value}</span>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{label}</span>
      </span>
    </div>
  )
}

export default function ArchitectureGraph({ documentId }: { documentId: string }) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['graph', documentId],
    queryFn: () => getRepoGraph(documentId),
    retry: 1,
  })

  const flow = useMemo(() => (data ? buildFlow(data) : null), [data])

  if (isLoading) {
    return (
      <div className="grid h-full grid-cols-4 gap-3 p-6">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (isError || !data || !flow) {
    return (
      <div className="p-8">
        <ErrorState
          message={`Failed to load graph${error instanceof Error ? `: ${error.message}` : ''}.`}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const languages = data.stats.languages ?? []

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        fitView
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
        minZoom={0.1}
      >
        <Background color="rgba(148,163,184,0.15)" gap={22} />
        <Controls className="!overflow-hidden !rounded-xl !border !border-white/10 !bg-slate-900/80 !shadow-soft" />
      </ReactFlow>

      <div className="surface absolute right-4 top-4 z-10 w-60 p-4">
        <p className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-300">
          <GitBranch className="h-3.5 w-3.5 text-violet-300" />
          Repository
        </p>
        <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
          <StatCard icon={<FileCode className="h-4 w-4" />} value={data.stats.file_count} label="files" />
          <StatCard icon={<Layers className="h-4 w-4" />} value={data.stats.edge_count} label="edges" />
        </div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-400">
          Languages
        </p>
        <ul className="space-y-1.5">
          {languages.map((lang) => (
            <li key={lang} className="flex items-center gap-2 text-xs text-slate-300">
              <span
                className="h-2.5 w-2.5 rounded-sm"
                style={{ background: colorForLanguage(lang, languages) }}
              />
              {lang}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
