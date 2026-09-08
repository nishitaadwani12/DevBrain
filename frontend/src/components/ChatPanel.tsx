import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { getFollowups, listMessages, streamAgent, streamChat } from '../lib/api'
import type { Citation, Confidence, MessageOut, ToolCall, ToolResult } from '../lib/types'
import CitationList from './CitationList'
import ConfidenceBadge from './ConfidenceBadge'

interface ChatPanelProps {
  workspaceId: string
  conversationId: string | null
  onConversationCreated: (conversationId: string) => void
}

interface ToolStep {
  name: string
  summary: string | null
}

const TOOL_ICONS: Record<string, string> = {
  search_documents: '🔍',
  explain_architecture: '📊',
  compare_documents: '⚖️',
}

function toolIcon(name: string): string {
  return TOOL_ICONS[name] ?? '🔧'
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

function ToolSteps({ steps }: { steps: ToolStep[] }) {
  if (!steps.length) return null
  return (
    <ul className="mb-3 space-y-1.5 border-b border-slate-800 pb-3">
      {steps.map((s, i) => (
        <li key={`${s.name}-${i}`} className="flex items-center gap-2 text-xs text-slate-400">
          <span>{toolIcon(s.name)}</span>
          <span className="font-mono text-slate-300">{s.name}</span>
          {s.summary === null ? (
            <span className="text-slate-500">…</span>
          ) : (
            <span className="text-slate-500">→ {s.summary}</span>
          )}
        </li>
      ))}
    </ul>
  )
}

export default function ChatPanel({
  workspaceId,
  conversationId,
  onConversationCreated,
}: ChatPanelProps) {
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [agentMode, setAgentMode] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamedAnswer, setStreamedAnswer] = useState('')
  const [streamedCitations, setStreamedCitations] = useState<Citation[]>([])
  const [toolSteps, setToolSteps] = useState<ToolStep[]>([])
  const [confidence, setConfidence] = useState<Confidence | null>(null)
  const [followups, setFollowups] = useState<string[]>([])
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
  }, [messages, streamedAnswer, toolSteps, followups])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [conversationId])

  const send = async (overrideQuery?: string) => {
    const query = (overrideQuery ?? input).trim()
    if (!query || streaming) return

    setInput('')
    setErrorMsg(null)
    setStreamedAnswer('')
    setStreamedCitations([])
    setToolSteps([])
    setConfidence(null)
    setFollowups([])
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
    let answerText = ''
    let latestConfidence: Confidence | null = null

    try {
      if (agentMode) {
        await streamAgent(
          workspaceId,
          { query, conversation_id: conversationId ?? undefined },
          {
            onConversation: ({ conversation_id }) => {
              newConversationId = conversation_id
              if (!conversationId) onConversationCreated(conversation_id)
            },
            onToolCall: (tool: ToolCall) =>
              setToolSteps((prev) => [...prev, { name: tool.name, summary: null }]),
            onToolResult: (result: ToolResult) =>
              setToolSteps((prev) => {
                const next = [...prev]
                // Fill the most recent pending step with the matching name.
                for (let i = next.length - 1; i >= 0; i--) {
                  if (next[i].name === result.name && next[i].summary === null) {
                    next[i] = { ...next[i], summary: result.summary }
                    return next
                  }
                }
                return [...next, { name: result.name, summary: result.summary }]
              }),
            onSources: (citations, conf) => {
              setStreamedCitations(citations)
              if (conf) {
                latestConfidence = conf
                setConfidence(conf)
              }
            },
            onAnswer: (text) => {
              answerText = text
              setStreamedAnswer(text)
            },
            onError: (message) => setErrorMsg(message),
          },
          controller.signal,
        )
      } else {
        await streamChat(
          workspaceId,
          { query, conversation_id: conversationId ?? undefined },
          {
            onConversation: ({ conversation_id }) => {
              newConversationId = conversation_id
              if (!conversationId) onConversationCreated(conversation_id)
            },
            onSources: (citations, conf) => {
              setStreamedCitations(citations)
              if (conf) {
                latestConfidence = conf
                setConfidence(conf)
              }
            },
            onToken: (text) => {
              answerText += text
              setStreamedAnswer((prev) => prev + text)
            },
            onError: (message) => setErrorMsg(message),
          },
          controller.signal,
        )
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setErrorMsg(err instanceof Error ? err.message : 'Streaming failed')
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
      const finalConvId = newConversationId ?? conversationId

      // Fetch follow-up suggestions from the completed answer.
      if (answerText && !controller.signal.aborted) {
        try {
          const { suggestions } = await getFollowups(workspaceId, query, answerText)
          setFollowups(suggestions.slice(0, 3))
        } catch {
          // Non-critical; ignore follow-up fetch failures.
        }
      }

      // Refetch persisted messages & conversations after the stream completes.
      await queryClient.invalidateQueries({ queryKey: ['messages', finalConvId] })
      await queryClient.invalidateQueries({
        queryKey: ['conversations', workspaceId],
      })

      // Keep confidence for the latest answer; clear the transient live bubble.
      setConfidence(latestConfidence)
      setStreamedAnswer('')
      setStreamedCitations([])
      setToolSteps([])
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  const hasContent = messages.length > 0 || streaming || streamedAnswer
  const showLiveBubble = streaming || Boolean(streamedAnswer) || toolSteps.length > 0
  const showFooter =
    !showLiveBubble && (Boolean(confidence) || followups.length > 0)

  return (
    <div className="flex h-full flex-col">
      {/* Chat header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-6 py-2.5">
        <span className="text-xs text-slate-500">
          {agentMode
            ? 'Agent mode: multi-step reasoning with tools'
            : 'Chat mode: grounded answers with citations'}
        </span>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
          <span>Agent mode</span>
          <button
            type="button"
            role="switch"
            aria-checked={agentMode}
            onClick={() => setAgentMode((v) => !v)}
            disabled={streaming}
            className={`relative h-5 w-9 rounded-full transition-colors disabled:opacity-50 ${
              agentMode ? 'bg-indigo-600' : 'bg-slate-700'
            }`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                agentMode ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </button>
        </label>
      </div>

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

        {showLiveBubble && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-slate-100">
              <ToolSteps steps={toolSteps} />
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
              {confidence && <ConfidenceBadge confidence={confidence} />}
            </div>
          </div>
        )}

        {showFooter && (
          <div className="flex justify-start">
            <div className="max-w-[85%]">
              {confidence && <ConfidenceBadge confidence={confidence} />}
              {followups.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Suggested follow-ups
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {followups.map((q) => (
                      <button
                        key={q}
                        type="button"
                        className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-left text-xs text-slate-200 transition-colors hover:border-indigo-500/50 hover:bg-indigo-500/10"
                        onClick={() => void send(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
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
