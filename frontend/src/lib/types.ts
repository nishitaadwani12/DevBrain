export interface WorkspaceSummary {
  id: string
  user_id: string
  name: string
  created_at: string
}

export type DocumentSourceType = 'upload' | 'github' | 'archive'
export type DocumentStatus = 'processing' | 'ready' | 'failed'

export type ConfidenceLabel = 'high' | 'medium' | 'low' | 'none'

export interface Confidence {
  score: number
  label: ConfidenceLabel
  grounded: boolean
}

export interface DocumentSummary {
  id: string
  workspace_id: string
  user_id: string
  filename: string
  file_type: string
  source_type: DocumentSourceType
  source_url: string | null
  status: DocumentStatus
  chunk_count: number
  error: string | null
  created_at: string
}

export interface ConversationSummary {
  id: string
  workspace_id: string
  title: string
  created_at: string
}

export type MessageRole = 'user' | 'assistant'

export interface Citation {
  index: number
  chunk_id: string
  document_id: string
  filename: string
  page: number | null
  source_path: string | null
  start_line: number | null
  end_line: number | null
  content: string
}

export interface MessageOut {
  id: string
  role: MessageRole
  content: string
  citations: Citation[]
  created_at: string
}

export interface GraphNode {
  id: string
  label: string
  dir: string
  language: string
}

export interface GraphEdge {
  source: string
  target: string
}

export interface GraphStats {
  file_count: number
  edge_count: number
  languages: string[]
}

export interface RepoGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: GraphStats
}

export interface AgentResponse {
  conversation_id: string
  answer: string
  citations: Citation[]
  tool_trace: unknown[]
}

export interface UploadResponse {
  document: DocumentSummary
  message: string
}

export interface RepoOverview {
  overview: string
}

export interface FollowupsResponse {
  suggestions: string[]
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
}

export interface ToolResult {
  name: string
  summary: string
}
