import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import {
  ArrowRight,
  Bot,
  GitCompareArrows,
  Loader2,
  Network,
  Search,
  Send,
  Sparkles,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { getFollowups, listMessages, streamAgent, streamChat } from '../lib/api'
import type { Citation, Confidence, MessageOut, ToolCall, ToolResult } from '../lib/types'
import { useToast } from '../context/ToastContext'
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

const TOOL_ICONS: Record<string, LucideIcon> = {
  search_documents: Search,
  explain_architecture: Network,
  compare_documents: GitCompareArrows,
}

function toolIcon(name: string): LucideIcon {
  return TOOL_ICONS[name] ?? Wrench
}

function MessageBubble({ message }: { message: MessageOut }) {
  const isUser = message.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      <span
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
          isUser
            ? 'bg-white/5 text-slate-300'
            : 'bg-brand-gradient text-white shadow-glow'
        }`}
      >
        {isUser ? <span className="text-xs font-semibold">You</span> : <Bot className="h-4 w-4" />}
      </span>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-indigo-600/90 text-white'
            : 'surface text-slate-100'
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
    </motion.div>
  )
}

function ToolSteps({ steps }: { steps: ToolStep[] }) {
  if (!steps.length) return null
  return (
    <div className="mb-3 border-b border-white/5 pb-3">
      <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-violet-300">
        <Sparkles className="h-3 w-3" />
        Agent reasoning
      </p>
      <ul className="space-y-1.5">
        <AnimatePresence initial={false}>
          {steps.map((s, i) => {
            const Icon = toolIcon(s.name)
            return (
              <motion.li
                key={`${s.name}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-2 text-xs"
              >
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-violet-500/15 text-violet-300">
                  <Icon className="h-3 w-3" />
                </span>
                <span className="font-mono text-slate-300">{s.name}</span>
                {s.summary === null ? (
                  <Loader2 className="h-3 w-3 animate-spin text-slate-500" />
                ) : (
                  <span className="text-slate-500">
                    <ArrowRight className="mr-1 inline h-3 w-3" />
                    {s.summary}
                  </span>
                )}
              </motion.li>
            )
          })}
        </AnimatePresence>
      </ul>
    </div>
  )
}

export default function ChatPanel({
  workspaceId,
  conversationId,
  onConversationCreated,
}: ChatPanelProps) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
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
    retry: 1,
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
        const msg = err instanceof Error ? err.message : 'Streaming failed'
        setErrorMsg(msg)
        toast(msg, 'error')
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
      const finalConvId = newConversationId ?? conversationId

      if (answerText && !controller.signal.aborted) {
        try {
          const { suggestions } = await getFollowups(workspaceId, query, answerText)
          setFollowups(suggestions.slice(0, 3))
        } catch {
          // Non-critical.
        }
      }

      await queryClient.invalidateQueries({ queryKey: ['messages', finalConvId] })
      await queryClient.invalidateQueries({
        queryKey: ['conversations', workspaceId],
      })

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
  const showFooter = !showLiveBubble && (Boolean(confidence) || followups.length > 0)

  return (
    <div className="flex h-full flex-col">
      {/* Chat header */}
      <div className="flex items-center justify-between border-b border-white/5 px-6 py-3">
        <span className="flex items-center gap-2 text-xs text-slate-500">
          {agentMode ? (
            <>
              <Sparkles className="h-3.5 w-3.5 text-violet-400" />
              Agent mode — multi-step reasoning with tools
            </>
          ) : (
            <>
              <Bot className="h-3.5 w-3.5 text-indigo-400" />
              Chat mode — grounded answers with citations
            </>
          )}
        </span>
        <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-300">
          <span>Agent mode</span>
          <button
            type="button"
            role="switch"
            aria-checked={agentMode}
            aria-label="Toggle agent mode"
            onClick={() => setAgentMode((v) => !v)}
            disabled={streaming}
            className={`relative h-5 w-9 rounded-full transition-colors disabled:opacity-50 ${
              agentMode ? 'bg-brand-gradient' : 'bg-slate-700'
            }`}
          >
            <motion.span
              layout
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow ${
                agentMode ? 'right-0.5' : 'left-0.5'
              }`}
            />
          </button>
        </label>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto p-6">
        {!hasContent && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 text-indigo-300">
              <Sparkles className="h-7 w-7" />
            </div>
            <p className="text-lg font-medium text-slate-100">Ask DevBrain anything</p>
            <p className="mt-1 max-w-sm text-sm text-slate-400">
              Ask questions about your uploaded documents and ingested repositories.
              Answers include citations to the source material.
            </p>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {showLiveBubble && (
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-glow">
              <Bot className="h-4 w-4" />
            </span>
            <div className="max-w-[80%] surface px-4 py-3 text-slate-100">
              <ToolSteps steps={toolSteps} />
              {streamedAnswer ? (
                <div className="prose-devbrain">
                  <ReactMarkdown>{streamedAnswer}</ReactMarkdown>
                </div>
              ) : (
                toolSteps.length === 0 && (
                  <span className="inline-flex gap-1 text-slate-500">
                    <span className="animate-bounce">•</span>
                    <span className="animate-bounce [animation-delay:150ms]">•</span>
                    <span className="animate-bounce [animation-delay:300ms]">•</span>
                  </span>
                )
              )}
              <CitationList citations={streamedCitations} />
              {confidence && <ConfidenceBadge confidence={confidence} />}
            </div>
          </div>
        )}

        {showFooter && (
          <div className="flex items-start gap-3">
            <span className="h-8 w-8 shrink-0" />
            <div className="max-w-[80%]">
              {confidence && <ConfidenceBadge confidence={confidence} />}
              {followups.length > 0 && (
                <div className="mt-3">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Suggested follow-ups
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {followups.map((q) => (
                      <motion.button
                        key={q}
                        type="button"
                        whileHover={{ y: -1 }}
                        whileTap={{ scale: 0.97 }}
                        className="chip"
                        onClick={() => void send(q)}
                      >
                        {q}
                        <ArrowRight className="h-3 w-3" />
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {errorMsg}
          </div>
        )}
      </div>

      <div className="border-t border-white/5 p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            className="input max-h-40 min-h-[46px] resize-none"
            placeholder="Ask a question…  (Enter to send, Shift+Enter for newline)"
            value={input}
            rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={streaming}
          />
          <motion.button
            type="button"
            whileTap={{ scale: 0.96 }}
            className="btn-primary h-[46px] px-4"
            onClick={() => void send()}
            disabled={streaming || !input.trim()}
          >
            {streaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </motion.button>
        </div>
      </div>
    </div>
  )
}
