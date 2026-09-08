import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { listMessages, streamChat } from '../lib/api'
import type { Citation, MessageOut } from '../lib/types'
import CitationList from './CitationList'

interface ChatPanelProps {
  workspaceId: string
  conversationId: string | null
  onConversationCreated: (conversationId: string) => void
}

function MessageBubble({ message }: { message: MessageOut }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'border border-slate-800 bg-slate-900/70 text-slate-100'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose-devbrain">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        {!isUser && <CitationList citations={message.citations} />}
      </div>
    </div>
  )
}

export default function ChatPanel({
  workspaceId,
  conversationId,
  onConversationCreated,
}: ChatPanelProps) {
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamedAnswer, setStreamedAnswer] = useState('')
  const [streamedCitations, setStreamedCitations] = useState<Citation[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const { data: messages = [] } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => listMessages(conversationId as string),
    enabled: Boolean(conversationId),
  })

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages, streamedAnswer])

  useEffect(() => {
    // Reset transient stream state when switching conversations.
    return () => abortRef.current?.abort()
  }, [conversationId])

  const send = async () => {
    const query = input.trim()
    if (!query || streaming) return

    setInput('')
    setErrorMsg(null)
    setStreamedAnswer('')
    setStreamedCitations([])
    setStreaming(true)

    // Optimistically show the user's message.
    const optimisticUser: MessageOut = {
      id: `optimistic-${Date.now()}`,
      role: 'user',
      content: query,
      citations: [],
      created_at: new Date().toISOString(),
    }
    queryClient.setQueryData<MessageOut[]>(
      ['messages', conversationId],
      (prev) => [...(prev ?? []), optimisticUser],
    )

    const controller = new AbortController()
    abortRef.current = controller
    let newConversationId: string | null = null

    try {
      await streamChat(
        workspaceId,
        {
          query,
          conversation_id: conversationId ?? undefined,
        },
        {
          onConversation: ({ conversation_id }) => {
            newConversationId = conversation_id
            if (!conversationId) onConversationCreated(conversation_id)
          },
          onSources: (citations) => setStreamedCitations(citations),
          onToken: (text) => setStreamedAnswer((prev) => prev + text),
          onDone: () => {},
          onError: (message) => setErrorMsg(message),
        },
        controller.signal,
      )
    } catch (err) {
      if (!controller.signal.aborted) {
        setErrorMsg(err instanceof Error ? err.message : 'Streaming failed')
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
      const finalConvId = newConversationId ?? conversationId
      // Refetch persisted messages & conversations after the stream completes.
      await queryClient.invalidateQueries({
        queryKey: ['messages', finalConvId],
      })
      await queryClient.invalidateQueries({
        queryKey: ['conversations', workspaceId],
      })
      setStreamedAnswer('')
      setStreamedCitations([])
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  const hasContent = messages.length > 0 || streaming || streamedAnswer

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-6">
        {!hasContent && (
          <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
            <p className="text-lg font-medium text-slate-300">Ask DevBrain anything</p>
            <p className="mt-1 max-w-sm text-sm">
              Ask questions about your uploaded documents and ingested repositories.
              Answers include citations to the source material.
            </p>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {(streaming || streamedAnswer) && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-slate-100">
              {streamedAnswer ? (
                <div className="prose-devbrain">
                  <ReactMarkdown>{streamedAnswer}</ReactMarkdown>
                </div>
              ) : (
                <span className="inline-flex gap-1 text-slate-500">
                  <span className="animate-bounce">•</span>
                  <span className="animate-bounce [animation-delay:150ms]">•</span>
                  <span className="animate-bounce [animation-delay:300ms]">•</span>
                </span>
              )}
              <CitationList citations={streamedCitations} />
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {errorMsg}
          </div>
        )}
      </div>

      <div className="border-t border-slate-800 p-4">
        <div className="flex items-end gap-2">
          <textarea
            className="input max-h-40 min-h-[44px] resize-none"
            placeholder="Ask a question…  (Enter to send, Shift+Enter for newline)"
            value={input}
            rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={streaming}
          />
          <button
            type="button"
            className="btn-primary h-[44px]"
            onClick={() => void send()}
            disabled={streaming || !input.trim()}
          >
            {streaming ? 'Sending…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
