import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Layout from '../components/Layout'
import {
  createWorkspace,
  deleteWorkspace,
  listWorkspaces,
} from '../lib/api'

export default function Workspaces() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [name, setName] = useState('')

  const { data: workspaces = [], isLoading, isError, error } = useQuery({
    queryKey: ['workspaces'],
    queryFn: listWorkspaces,
  })

  const createMutation = useMutation({
    mutationFn: (n: string) => createWorkspace(n),
    onSuccess: (ws) => {
      setName('')
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      navigate(`/w/${ws.id}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  return (
    <Layout>
      <div className="mx-auto max-w-3xl p-8">
        <h1 className="text-2xl font-semibold text-slate-100">Workspaces</h1>
        <p className="mt-1 text-sm text-slate-400">
          Group your documents and repositories, then chat with them.
        </p>

        <form
          className="mt-6 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) createMutation.mutate(name.trim())
          }}
        >
          <input
            className="input"
            placeholder="New workspace name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            type="submit"
            className="btn-primary shrink-0"
            disabled={createMutation.isPending || !name.trim()}
          >
            {createMutation.isPending ? 'Creating…' : 'Create'}
          </button>
        </form>

        <div className="mt-8">
          {isLoading && <p className="text-sm text-slate-400">Loading workspaces…</p>}
          {isError && (
            <p className="text-sm text-red-400">
              Failed to load workspaces
              {error instanceof Error ? `: ${error.message}` : ''}.
            </p>
          )}

          {!isLoading && !isError && workspaces.length === 0 && (
            <p className="text-sm text-slate-500">
              No workspaces yet. Create one to get started.
            </p>
          )}

          <ul className="grid gap-3 sm:grid-cols-2">
            {workspaces.map((ws) => (
              <li
                key={ws.id}
                className="card group flex items-center justify-between transition-colors hover:border-indigo-500/50"
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => navigate(`/w/${ws.id}`)}
                >
                  <span className="block truncate text-base font-medium text-slate-100">
                    {ws.name}
                  </span>
                  <span className="mt-1 block text-xs text-slate-500">
                    Created {new Date(ws.created_at).toLocaleDateString()}
                  </span>
                </button>
                <button
                  type="button"
                  className="ml-3 shrink-0 text-xs text-slate-500 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm(`Delete workspace "${ws.name}"?`)) {
                      deleteMutation.mutate(ws.id)
                    }
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Layout>
  )
}
