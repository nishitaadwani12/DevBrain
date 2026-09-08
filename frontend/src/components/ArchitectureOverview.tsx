import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import ReactMarkdown from 'react-markdown'
import { getRepoOverview } from '../lib/api'

export default function ArchitectureOverview({ documentId }: { documentId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['overview', documentId],
    queryFn: () => getRepoOverview(documentId),
    retry: false,
    // Re-check periodically while the overview is still being generated (404).
    refetchInterval: (query) => (query.state.error ? 5000 : false),
  })

  if (isLoading) {
    return <div className="p-6 text-sm text-slate-400">Loading overview…</div>
  }

  const status = error instanceof AxiosError ? error.response?.status : undefined

  if (error) {
    if (status === 404) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-slate-400">
          <span className="inline-flex gap-1 text-slate-500">
            <span className="animate-bounce">•</span>
            <span className="animate-bounce [animation-delay:150ms]">•</span>
            <span className="animate-bounce [animation-delay:300ms]">•</span>
          </span>
          <p>Generating AI architecture overview…</p>
          <p className="text-xs text-slate-500">This may take a moment. It will appear automatically.</p>
        </div>
      )
    }
    return (
      <div className="p-6 text-sm text-red-400">
        Failed to load overview
        {error instanceof Error ? `: ${error.message}` : ''}.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="prose-devbrain mx-auto max-w-3xl">
        <ReactMarkdown>{data?.overview ?? ''}</ReactMarkdown>
      </div>
    </div>
  )
}
