import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Loader2, Sparkles } from 'lucide-react'
import { getRepoOverview } from '../lib/api'
import { Skeleton } from './ui/Skeleton'
import { ErrorState } from './ui/States'

export default function ArchitectureOverview({ documentId }: { documentId: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['overview', documentId],
    queryFn: () => getRepoOverview(documentId),
    retry: false,
    refetchInterval: (query) => (query.state.error ? 5000 : false),
  })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-8">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  const status = error instanceof AxiosError ? error.response?.status : undefined

  if (error) {
    if (status === 404) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 text-indigo-300">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
          <p className="text-base font-medium text-slate-200">
            Generating AI architecture overview…
          </p>
          <p className="max-w-sm text-xs text-slate-500">
            This may take a moment. It will appear automatically when ready.
          </p>
        </div>
      )
    }
    return (
      <div className="p-8">
        <ErrorState
          message={`Failed to load overview${error instanceof Error ? `: ${error.message}` : ''}.`}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-8">
      <motion.article
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="surface mx-auto max-w-3xl p-8"
      >
        <div className="mb-6 flex items-center gap-2 border-b border-white/5 pb-4">
          <Sparkles className="h-4 w-4 text-violet-300" />
          <h1 className="text-sm font-semibold uppercase tracking-wide text-slate-300">
            AI Architecture Overview
          </h1>
        </div>
        <div className="prose-devbrain">
          <ReactMarkdown>{data?.overview ?? ''}</ReactMarkdown>
        </div>
      </motion.article>
    </div>
  )
}
