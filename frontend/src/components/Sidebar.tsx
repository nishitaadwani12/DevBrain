import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteDocument,
  ingestRepo,
  listConversations,
  listDocuments,
  uploadDocument,
} from '../lib/api'
import type { DocumentSummary } from '../lib/types'
import DocumentStatusBadge from './DocumentStatusBadge'

interface SidebarProps {
  workspaceId: string
  selectedDocumentId: string | null
  onSelectDocument: (doc: DocumentSummary) => void
  selectedConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
}

export default function Sidebar({
  workspaceId,
  selectedDocumentId,
  onSelectDocument,
  selectedConversationId,
  onSelectConversation,
  onNewConversation,
}: SidebarProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [repoUrl, setRepoUrl] = useState('')
  const [showRepoForm, setShowRepoForm] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const documentsQuery = useQuery({
    queryKey: ['documents', workspaceId],
    queryFn: () => listDocuments(workspaceId),
    // Poll while anything is still processing so the UI updates on completion.
    refetchInterval: (query) => {
      const docs = query.state.data
      return docs?.some((d) => d.status === 'processing') ? 3000 : false
    },
  })

  const conversationsQuery = useQuery({
    queryKey: ['conversations', workspaceId],
    queryFn: () => listConversations(workspaceId),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(workspaceId, file),
    onSuccess: () => {
      setActionError(null)
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
    onError: (err) =>
      setActionError(err instanceof Error ? err.message : 'Upload failed'),
  })

  const ingestMutation = useMutation({
    mutationFn: (url: string) => ingestRepo(workspaceId, url),
    onSuccess: () => {
      setActionError(null)
      setRepoUrl('')
      setShowRepoForm(false)
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
    onError: (err) =>
      setActionError(err instanceof Error ? err.message : 'Repo ingest failed'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] }),
  })

  const documents = documentsQuery.data ?? []
  const conversations = conversationsQuery.data ?? []

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadMutation.mutate(file)
    e.target.value = ''
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-slate-800 bg-slate-900/40">
      {/* Documents */}
      <div className="flex flex-col gap-3 border-b border-slate-800 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Documents
          </h2>
          <div className="flex gap-1.5">
            <button
              type="button"
              className="btn-ghost px-2 py-1 text-xs"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
            </button>
            <button
              type="button"
              className="btn-ghost px-2 py-1 text-xs"
              onClick={() => setShowRepoForm((v) => !v)}
            >
              + Repo
            </button>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.md,.txt,.zip"
          onChange={onFileChange}
        />
        <p className="text-[10px] text-slate-500">
          Allowed: pdf, docx, md, txt, zip
        </p>

        {showRepoForm && (
          <form
            className="flex flex-col gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (repoUrl.trim()) ingestMutation.mutate(repoUrl.trim())
            }}
          >
            <input
              className="input text-xs"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <button
              type="submit"
              className="btn-primary py-1.5 text-xs"
              disabled={ingestMutation.isPending || !repoUrl.trim()}
            >
              {ingestMutation.isPending ? 'Ingesting…' : 'Add GitHub repo'}
            </button>
          </form>
        )}

        {actionError && (
          <p className="text-xs text-red-400">{actionError}</p>
        )}

        <ul className="flex flex-col gap-1.5">
          {documents.length === 0 && (
            <li className="text-xs text-slate-500">No documents yet.</li>
          )}
          {documents.map((doc) => (
            <li
              key={doc.id}
              className={`group flex flex-col gap-1 rounded-lg border p-2 transition-colors ${
                selectedDocumentId === doc.id
                  ? 'border-indigo-500/50 bg-indigo-500/10'
                  : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
              }`}
            >
              <button
                type="button"
                className="flex items-start gap-2 text-left"
                onClick={() => onSelectDocument(doc)}
              >
                <span className="mt-0.5 text-xs">
                  {doc.source_type === 'github'
                    ? '🗂️'
                    : doc.source_type === 'archive'
                      ? '🗜️'
                      : '📄'}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-200">
                      {doc.filename}
                    </span>
                    {doc.source_type === 'archive' && (
                      <span className="shrink-0 rounded bg-slate-700 px-1 py-0.5 text-[9px] font-medium uppercase text-slate-300">
                        zip
                      </span>
                    )}
                  </span>
                  <span className="mt-1 flex items-center gap-2">
                    <DocumentStatusBadge status={doc.status} />
                    {doc.status === 'ready' && (
                      <span className="text-[10px] text-slate-500">
                        {doc.chunk_count} chunks
                      </span>
                    )}
                  </span>
                </span>
              </button>
              {doc.status === 'failed' && doc.error && (
                <p className="truncate text-[10px] text-red-400" title={doc.error}>
                  {doc.error}
                </p>
              )}
              <button
                type="button"
                className="self-end text-[10px] text-slate-500 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                onClick={() => deleteMutation.mutate(doc.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Conversations */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
            Conversations
          </h2>
          <button
            type="button"
            className="btn-ghost px-2 py-1 text-xs"
            onClick={onNewConversation}
          >
            + New
          </button>
        </div>

        <ul className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
          {conversations.length === 0 && (
            <li className="text-xs text-slate-500">No conversations yet.</li>
          )}
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  selectedConversationId === c.id
                    ? 'bg-indigo-500/15 text-indigo-200'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
                onClick={() => onSelectConversation(c.id)}
              >
                {c.title || 'Untitled conversation'}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}
