import axios from 'axios'
import { getAccessToken } from './supabase'
import type {
  AgentResponse,
  Citation,
  Confidence,
  ConversationSummary,
  DocumentSummary,
  FollowupsResponse,
  MessageOut,
  RepoGraph,
  RepoOverview,
  ToolCall,
  ToolResult,
  UploadResponse,
  WorkspaceSummary,
} from './types'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
})

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---------- Workspaces ----------

export async function createWorkspace(name: string): Promise<WorkspaceSummary> {
  const { data } = await api.post<WorkspaceSummary>('/workspaces', { name })
  return data
}

export async function listWorkspaces(): Promise<WorkspaceSummary[]> {
  const { data } = await api.get<WorkspaceSummary[]>('/workspaces')
  return data
}

export async function getWorkspace(id: string): Promise<WorkspaceSummary> {
  const { data } = await api.get<WorkspaceSummary>(`/workspaces/${id}`)
  return data
}

export async function deleteWorkspace(id: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(`/workspaces/${id}`)
  return data
}

// ---------- Documents ----------

export async function uploadDocument(
  workspaceId: string,
  file: File,
): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<UploadResponse>(
    `/workspaces/${workspaceId}/documents/upload`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function listDocuments(workspaceId: string): Promise<DocumentSummary[]> {
  const { data } = await api.get<DocumentSummary[]>(
    `/workspaces/${workspaceId}/documents`,
  )
  return data
}

export async function deleteDocument(id: string): Promise<{ deleted: boolean }> {
  const { data } = await api.delete<{ deleted: boolean }>(`/documents/${id}`)
  return data
}

export async function ingestRepo(
  workspaceId: string,
  url: string,
): Promise<UploadResponse> {
  const { data } = await api.post<UploadResponse>(
    `/workspaces/${workspaceId}/repos/ingest`,
    { url },
  )
  return data
}

export async function getRepoGraph(documentId: string): Promise<RepoGraph> {
  const { data } = await api.get<RepoGraph>(`/repos/${documentId}/graph`)
  return data
}

export async function getRepoOverview(documentId: string): Promise<RepoOverview> {
  const { data } = await api.get<RepoOverview>(`/repos/${documentId}/overview`)
  return data
}

// ---------- Follow-up suggestions ----------

export async function getFollowups(
  workspaceId: string,
  question: string,
  answer: string,
): Promise<FollowupsResponse> {
  const { data } = await api.post<FollowupsResponse>(
    `/workspaces/${workspaceId}/followups`,
    { question, answer },
  )
  return data
}

// ---------- Conversations & messages ----------

export async function listConversations(
  workspaceId: string,
): Promise<ConversationSummary[]> {
  const { data } = await api.get<ConversationSummary[]>(
    `/workspaces/${workspaceId}/conversations`,
  )
  return data
}

export async function listMessages(conversationId: string): Promise<MessageOut[]> {
  const { data } = await api.get<MessageOut[]>(
    `/conversations/${conversationId}/messages`,
  )
  return data
}

// ---------- Agent (non-streaming) ----------

export interface AgentRequest {
  query: string
  conversation_id?: string
}

export async function runAgent(
  workspaceId: string,
  body: AgentRequest,
): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>(
    `/workspaces/${workspaceId}/agent`,
    body,
  )
  return data
}

// ---------- Chat (SSE over fetch) ----------

export interface ChatRequest {
  query: string
  top_k?: number
  conversation_id?: string
}

export interface StreamChatHandlers {
  onConversation?: (data: { conversation_id: string; title: string }) => void
  onSources?: (citations: Citation[], confidence?: Confidence) => void
  onToken?: (text: string) => void
  onDone?: () => void
  onError?: (message: string) => void
}

type SSEDispatch = (eventName: string, payload: unknown) => void

/**
 * Shared SSE-over-fetch reader. EventSource only supports GET, so we POST and
 * read the response body as a stream, parsing `event:` / `data:` lines and
 * invoking `dispatch(eventName, payload)` for each complete event.
 */
async function consumeSSE(
  path: string,
  body: unknown,
  onError: (message: string) => void,
  dispatch: SSEDispatch,
  signal?: AbortSignal,
): Promise<void> {
  const token = await getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    onError(text || `Request failed with status ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const parseAndDispatch = (rawEvent: string) => {
    const lines = rawEvent.split('\n')
    let eventName = 'message'
    const dataLines: string[] = []
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
    const dataStr = dataLines.join('\n')
    let payload: unknown = {}
    if (dataStr) {
      try {
        payload = JSON.parse(dataStr)
      } catch {
        payload = { text: dataStr }
      }
    }
    dispatch(eventName, payload)
  }

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sepIndex: number
    // SSE events are separated by a blank line (\n\n).
    while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex)
      buffer = buffer.slice(sepIndex + 2)
      if (rawEvent.trim()) parseAndDispatch(rawEvent)
    }
  }

  if (buffer.trim()) parseAndDispatch(buffer)
}

/**
 * Streams a chat response (token-by-token) from POST /workspaces/{id}/chat.
 */
export async function streamChat(
  workspaceId: string,
  body: ChatRequest,
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await consumeSSE(
    `/workspaces/${workspaceId}/chat`,
    body,
    (msg) => handlers.onError?.(msg),
    (eventName, payload) => {
      switch (eventName) {
        case 'conversation':
          handlers.onConversation?.(
            payload as { conversation_id: string; title: string },
          )
          break
        case 'sources': {
          const p = payload as { citations: Citation[]; confidence?: Confidence }
          handlers.onSources?.(p.citations ?? [], p.confidence)
          break
        }
        case 'token':
          handlers.onToken?.((payload as { text: string }).text ?? '')
          break
        case 'done':
          handlers.onDone?.()
          break
        case 'error':
          handlers.onError?.(
            (payload as { message: string }).message ?? 'Unknown error',
          )
          break
        default:
          break
      }
    },
    signal,
  )
}

// ---------- Agent (streaming) ----------

export interface AgentStreamRequest {
  query: string
  conversation_id?: string
}

export interface StreamAgentHandlers {
  onConversation?: (data: { conversation_id: string; title: string }) => void
  onToolCall?: (tool: ToolCall) => void
  onToolResult?: (result: ToolResult) => void
  onSources?: (citations: Citation[], confidence?: Confidence) => void
  onAnswer?: (text: string) => void
  onDone?: () => void
  onError?: (message: string) => void
}

/**
 * Streams an agent-mode response from POST /workspaces/{id}/agent/stream.
 * Emits interleaved tool_call / tool_result events, then sources, then the
 * FULL answer in a single `answer` event (not token-by-token).
 */
export async function streamAgent(
  workspaceId: string,
  body: AgentStreamRequest,
  handlers: StreamAgentHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await consumeSSE(
    `/workspaces/${workspaceId}/agent/stream`,
    body,
    (msg) => handlers.onError?.(msg),
    (eventName, payload) => {
      switch (eventName) {
        case 'conversation':
          handlers.onConversation?.(
            payload as { conversation_id: string; title: string },
          )
          break
        case 'tool_call':
          handlers.onToolCall?.(payload as ToolCall)
          break
        case 'tool_result':
          handlers.onToolResult?.(payload as ToolResult)
          break
        case 'sources': {
          const p = payload as { citations: Citation[]; confidence?: Confidence }
          handlers.onSources?.(p.citations ?? [], p.confidence)
          break
        }
        case 'answer':
          handlers.onAnswer?.((payload as { text: string }).text ?? '')
          break
        case 'done':
          handlers.onDone?.()
          break
        case 'error':
          handlers.onError?.(
            (payload as { message: string }).message ?? 'Unknown error',
          )
          break
        default:
          break
      }
    },
    signal,
  )
}
