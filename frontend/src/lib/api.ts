import axios from 'axios'
import { getAccessToken } from './supabase'
import type {
  AgentResponse,
  Citation,
  ConversationSummary,
  DocumentSummary,
  MessageOut,
  RepoGraph,
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
  onSources?: (citations: Citation[]) => void
  onToken?: (text: string) => void
  onDone?: () => void
  onError?: (message: string) => void
}

/**
 * Streams a chat response using the SSE-over-fetch pattern. EventSource only
 * supports GET, so we read the response body as a stream and parse the
 * `event:` / `data:` lines ourselves.
 */
export async function streamChat(
  workspaceId: string,
  body: ChatRequest,
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = await getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_URL}/workspaces/${workspaceId}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    handlers.onError?.(text || `Request failed with status ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (rawEvent: string) => {
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

    switch (eventName) {
      case 'conversation':
        handlers.onConversation?.(
          payload as { conversation_id: string; title: string },
        )
        break
      case 'sources':
        handlers.onSources?.((payload as { citations: Citation[] }).citations ?? [])
        break
      case 'token':
        handlers.onToken?.((payload as { text: string }).text ?? '')
        break
      case 'done':
        handlers.onDone?.()
        break
      case 'error':
        handlers.onError?.((payload as { message: string }).message ?? 'Unknown error')
        break
      default:
        break
    }
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
      if (rawEvent.trim()) dispatch(rawEvent)
    }
  }

  if (buffer.trim()) dispatch(buffer)
}
