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
import { getRepoGraph } from '../lib/api'
import type { RepoGraph } from '../lib/types'

// Deterministic color per language.
const LANGUAGE_COLORS = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#ec4899',
  '#06b6d4',
  '#a855f7',
  '#ef4444',
  '#14b8a6',
  '#eab308',
  '#3b82f6',
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
  const gapX = 200
  const gapY = 90

  const nodes: Node[] = graph.nodes.map((n, i) => {
    const color = colorForLanguage(n.language, languages)
    return {
      id: n.id,
      position: { x: (i % cols) * gapX, y: Math.floor(i / cols) * gapY },
      data: { label: n.label },
      style: {
        background: '#0f172a',
        border: `1px solid ${color}`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 8,
        color: '#e2e8f0',
        fontSize: 11,
        padding: '6px 10px',
        width: 160,
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
      style: { stroke: '#334155' },
      animated: false,
    }))

  return { nodes, edges }
}

export default function ArchitectureGraph({ documentId }: { documentId: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['graph', documentId],
    queryFn: () => getRepoGraph(documentId),
  })

  const flow = useMemo(() => (data ? buildFlow(data) : null), [data])

  if (isLoading) {
    return <div className="p-6 text-sm text-slate-400">Loading architecture graph…</div>
  }

  if (isError || !data || !flow) {
    return (
      <div className="p-6 text-sm text-red-400">
        Failed to load graph{error instanceof Error ? `: ${error.message}` : ''}.
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
        <Background color="#1e293b" gap={20} />
        <Controls className="!bg-slate-800 !text-slate-200" />
      </ReactFlow>

      <div className="absolute right-3 top-3 z-10 w-56 rounded-xl border border-slate-800 bg-slate-900/90 p-3 text-xs backdrop-blur">
        <p className="mb-2 font-semibold text-slate-200">Repository stats</p>
        <div className="mb-3 grid grid-cols-2 gap-2 text-slate-400">
          <div>
            <span className="block text-lg font-semibold text-slate-100">
              {data.stats.file_count}
            </span>
            files
          </div>
          <div>
            <span className="block text-lg font-semibold text-slate-100">
              {data.stats.edge_count}
            </span>
            edges
          </div>
        </div>
        <p className="mb-1 font-medium text-slate-300">Languages</p>
        <ul className="space-y-1">
          {languages.map((lang) => (
            <li key={lang} className="flex items-center gap-2 text-slate-400">
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
