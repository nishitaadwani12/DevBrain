import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import {
  FileStack,
  GitBranch,
  MessagesSquare,
  Plus,
  Trash2,
  Upload,
} from 'lucide-react'
import {
  deleteDocument,
  ingestRepo,
  listConversations,
  listDocuments,
  uploadDocument,
} from '../lib/api'
import type { DocumentSummary } from '../lib/types'
import { useToast } from '../context/ToastContext'
import DocumentStatusBadge from './DocumentStatusBadge'
import DocumentIcon from './DocumentIcon'
import { ListItemSkeleton } from './ui/Skeleton'
import { ErrorState } from './ui/States'

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
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [repoUrl, setRepoUrl] = useState('')
  const [showRepoForm, setShowRepoForm] = useState(false)

  const documentsQuery = useQuery({
    queryKey: ['documents', workspaceId],
    queryFn: () => listDocuments(workspaceId),
    retry: 1,
    // Poll while anything is still processing so the UI updates on completion.
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.status === 'processing') ? 3000 : false,
  })

  const conversationsQuery = useQuery({
    queryKey: ['conversations', workspaceId],
    queryFn: () => listConversations(workspaceId),
    retry: 1,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(workspaceId, file),
    onMutate: () => toast('Upload started — processing document…', 'info'),
    onSuccess: (res) => {
      toast(`"${res.document.filename}" uploaded`, 'success')
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
    onError: (err) =>
      toast(err instanceof Error ? err.message : 'Upload failed', 'error'),
  })

  const ingestMutation = useMutation({
    mutationFn: (url: string) => ingestRepo(workspaceId, url),
    onMutate: () => toast('Ingesting repository…', 'info'),
    onSuccess: () => {
      toast('Repository ingestion started', 'success')
      setRepoUrl('')
      setShowRepoForm(false)
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
    onError: (err) =>
      toast(err instanceof Error ? err.message : 'Repo ingest failed', 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      toast('Document deleted', 'success')
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
    onError: () => toast('Failed to delete document', 'error'),
  })

  const documents = documentsQuery.data ?? []
  const conversations = conversationsQuery.data ?? []

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadMutation.mutate(file)
    e.target.value = ''
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-white/5 bg-slate-950/40 backdrop-blur-xl">
      {/* Documents */}
      <div className="flex min-h-0 flex-[3] flex-col border-b border-white/5">
        <div className="flex items-center justify-between px-4 pt-4">
          <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <FileStack className="h-3.5 w-3.5" />
            Knowledge
          </h2>
          <div className="flex gap-1.5">
            <button
              type="button"
              className="btn-secondary px-2 py-1 text-xs"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload className="h-3.5 w-3.5" />
              {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
            </button>
            <button
              type="button"
              className="btn-secondary px-2 py-1 text-xs"
              onClick={() => setShowRepoForm((v) => !v)}
              aria-expanded={showRepoForm}
            >
              <GitBranch className="h-3.5 w-3.5" />
              Repo
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

        <div className="px-4 pt-2">
          <p className="text-[10px] text-slate-500">Allowed: pdf, docx, md, txt, zip</p>
        </div>

        <AnimatePresence>
          {showRepoForm && (
            <motion.form
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden px-4"
              onSubmit={(e) => {
                e.preventDefault()
                if (repoUrl.trim()) ingestMutation.mutate(repoUrl.trim())
              }}
            >
              <div className="flex flex-col gap-2 pt-3">
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
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        <div className="mt-3 flex-1 space-y-1.5 overflow-y-auto px-4 pb-4">
          {documentsQuery.isLoading && (
            <>
              <ListItemSkeleton />
              <ListItemSkeleton />
              <ListItemSkeleton />
            </>
          )}

          {documentsQuery.isError && (
            <ErrorState
              compact
              message="Couldn't load documents."
              onRetry={() => documentsQuery.refetch()}
            />
          )}

          {!documentsQuery.isLoading && !documentsQuery.isError && documents.length === 0 && (
            <p className="rounded-xl border border-dashed border-white/10 p-4 text-center text-xs text-slate-500">
              No documents yet. Upload a file or add a repo to get started.
            </p>
          )}

          <AnimatePresence initial={false}>
            {documents.map((doc, i) => (
              <motion.div
                key={doc.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.18, delay: Math.min(i * 0.03, 0.2) }}
                className={`group rounded-xl border p-2.5 transition-colors ${
                  selectedDocumentId === doc.id
                    ? 'border-indigo-500/40 bg-indigo-500/10 shadow-glow'
                    : 'border-white/5 bg-slate-900/40 hover:border-white/10 hover:bg-slate-900/70'
                }`}
              >
                <button
                  type="button"
                  className="flex w-full items-start gap-2.5 text-left"
                  onClick={() => onSelectDocument(doc)}
                >
                  <DocumentIcon doc={doc} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5">
                      <span className="min-w-0 flex-1 truncate text-sm text-slate-200">
                        {doc.filename}
                      </span>
                      {doc.source_type === 'archive' && (
                        <span className="shrink-0 rounded bg-white/10 px-1 py-0.5 text-[9px] font-semibold uppercase text-slate-300">
                          zip
                        </span>
                      )}
                    </span>
                    <span className="mt-1.5 flex flex-wrap items-center gap-2">
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
                  <p className="mt-1.5 truncate text-[10px] text-red-400" title={doc.error}>
                    {doc.error}
                  </p>
                )}
                <div className="mt-1 flex justify-end">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-[10px] text-slate-500 opacity-0 transition-all hover:text-red-400 group-hover:opacity-100"
                    onClick={() => deleteMutation.mutate(doc.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Conversations */}
      <div className="flex min-h-0 flex-[2] flex-col">
        <div className="flex items-center justify-between px-4 pt-4">
          <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <MessagesSquare className="h-3.5 w-3.5" />
            Conversations
          </h2>
          <button
            type="button"
            className="btn-secondary px-2 py-1 text-xs"
            onClick={onNewConversation}
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
        </div>

        <div className="mt-3 flex-1 space-y-1 overflow-y-auto px-4 pb-4">
          {conversationsQuery.isLoading && (
            <>
              <ListItemSkeleton />
              <ListItemSkeleton />
            </>
          )}
          {!conversationsQuery.isLoading && conversations.length === 0 && (
            <p className="px-1 text-xs text-slate-500">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`flex w-full items-center gap-2 truncate rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                selectedConversationId === c.id
                  ? 'bg-indigo-500/15 text-indigo-100'
                  : 'text-slate-300 hover:bg-white/5'
              }`}
              onClick={() => onSelectConversation(c.id)}
            >
              <MessagesSquare className="h-3.5 w-3.5 shrink-0 text-slate-500" />
              <span className="truncate">{c.title || 'Untitled conversation'}</span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
