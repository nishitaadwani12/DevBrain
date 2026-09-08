import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowRight, Boxes, Loader2, Plus, Sparkles, Trash2 } from 'lucide-react'
import Layout from '../components/Layout'
import { createWorkspace, deleteWorkspace, listWorkspaces } from '../lib/api'
import { useToast } from '../context/ToastContext'
import { CardSkeleton } from '../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../components/ui/States'
import type { WorkspaceSummary } from '../lib/types'

export default function Workspaces() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [name, setName] = useState('')

  const workspacesQuery = useQuery({
    queryKey: ['workspaces'],
    queryFn: listWorkspaces,
    retry: 1,
  })

  const createMutation = useMutation({
    mutationFn: (n: string) => createWorkspace(n),
    onSuccess: (ws) => {
      setName('')
      toast(`Workspace "${ws.name}" created`, 'success')
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      navigate(`/w/${ws.id}`)
    },
    onError: (err) =>
      toast(err instanceof Error ? err.message : 'Failed to create workspace', 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: () => {
      toast('Workspace deleted', 'success')
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
    onError: () => toast('Failed to delete workspace', 'error'),
  })

  const workspaces = workspacesQuery.data ?? []

  const CreateForm = (
    <form
      className="flex w-full max-w-md gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        if (name.trim()) createMutation.mutate(name.trim())
      }}
    >
      <input
        className="input"
        placeholder="Name your workspace…"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button
        type="submit"
        className="btn-primary shrink-0"
        disabled={createMutation.isPending || !name.trim()}
      >
        {createMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Plus className="h-4 w-4" />
        )}
        Create
      </button>
    </form>
  )

  return (
    <Layout>
      <div className="mx-auto max-w-5xl px-6 py-10">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mb-10"
        >
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
            <Sparkles className="h-3 w-3 text-violet-300" />
            AI knowledge agent
          </span>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white">
            Your <span className="brand-text">workspaces</span>
          </h1>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Group documents and repositories, then chat with an agent that answers with
            citations and can reason across your knowledge base.
          </p>
          <div className="mt-6">{CreateForm}</div>
        </motion.div>

        {/* Content */}
        {workspacesQuery.isLoading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        )}

        {workspacesQuery.isError && (
          <ErrorState
            message="Couldn't load your workspaces."
            onRetry={() => workspacesQuery.refetch()}
          />
        )}

        {!workspacesQuery.isLoading && !workspacesQuery.isError && workspaces.length === 0 && (
          <EmptyState
            icon={<Boxes className="h-6 w-6" />}
            title="No workspaces yet"
            description="Create your first workspace above to start uploading documents and chatting with your knowledge."
          />
        )}

        {workspaces.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {workspaces.map((ws, i) => (
              <WorkspaceCard
                key={ws.id}
                ws={ws}
                index={i}
                onOpen={() => navigate(`/w/${ws.id}`)}
                onDelete={() => {
                  if (confirm(`Delete workspace "${ws.name}"?`)) {
                    deleteMutation.mutate(ws.id)
                  }
                }}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

function WorkspaceCard({
  ws,
  index,
  onOpen,
  onDelete,
}: {
  ws: WorkspaceSummary
  index: number
  onOpen: () => void
  onDelete: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.05, 0.3) }}
      whileHover={{ y: -4 }}
      className="group relative"
    >
      <button
        type="button"
        onClick={onOpen}
        className="surface relative w-full overflow-hidden p-5 text-left transition-shadow hover:shadow-lift"
      >
        {/* gradient top accent */}
        <span className="absolute inset-x-0 top-0 h-1 bg-brand-gradient opacity-70" />
        <div className="flex items-start justify-between">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/25 to-violet-500/25 text-indigo-200">
            <Boxes className="h-5 w-5" />
          </span>
          <ArrowRight className="h-4 w-4 text-slate-600 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-300" />
        </div>
        <h3 className="mt-4 truncate text-lg font-semibold text-slate-100">{ws.name}</h3>
        <p className="mt-1 text-xs text-slate-500">
          Created {new Date(ws.created_at).toLocaleDateString()}
        </p>
      </button>
      <button
        type="button"
        className="absolute bottom-4 right-4 inline-flex items-center gap-1 text-[10px] text-slate-500 opacity-0 transition-all hover:text-red-400 group-hover:opacity-100"
        onClick={onDelete}
      >
        <Trash2 className="h-3 w-3" />
        Delete
      </button>
    </motion.div>
  )
}
