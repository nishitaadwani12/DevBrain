import { useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Layout from '../components/Layout'
import Sidebar from '../components/Sidebar'
import ChatPanel from '../components/ChatPanel'
import ArchitectureGraph from '../components/ArchitectureGraph'
import ArchitectureOverview from '../components/ArchitectureOverview'
import { getWorkspace } from '../lib/api'
import type { DocumentSummary } from '../lib/types'

type Tab = 'chat' | 'overview' | 'architecture'

export default function Workspace() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [tab, setTab] = useState<Tab>('chat')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [selectedDoc, setSelectedDoc] = useState<DocumentSummary | null>(null)

  const { data: workspace } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => getWorkspace(workspaceId as string),
    enabled: Boolean(workspaceId),
  })

  if (!workspaceId) {
    return <Navigate to="/" replace />
  }

  const isRepoSelected = selectedDoc?.source_type === 'github'

  const onSelectDocument = (doc: DocumentSummary) => {
    setSelectedDoc(doc)
    if (doc.source_type === 'github') {
      setTab('overview')
    }
  }

  return (
    <Layout>
      <div className="flex h-full">
        <Sidebar
          workspaceId={workspaceId}
          selectedDocumentId={selectedDoc?.id ?? null}
          onSelectDocument={onSelectDocument}
          selectedConversationId={conversationId}
          onSelectConversation={(id) => {
            setConversationId(id)
            setTab('chat')
          }}
          onNewConversation={() => {
            setConversationId(null)
            setTab('chat')
          }}
        />

        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-1 border-b border-slate-800 px-4">
            <span className="mr-4 truncate py-3 text-sm font-medium text-slate-300">
              {workspace?.name ?? 'Workspace'}
            </span>
            <TabButton active={tab === 'chat'} onClick={() => setTab('chat')}>
              Chat
            </TabButton>
            <TabButton
              active={tab === 'overview'}
              disabled={!isRepoSelected}
              onClick={() => isRepoSelected && setTab('overview')}
            >
              Overview
            </TabButton>
            <TabButton
              active={tab === 'architecture'}
              disabled={!isRepoSelected}
              onClick={() => isRepoSelected && setTab('architecture')}
            >
              Architecture
            </TabButton>
          </div>

          <div className="min-h-0 flex-1">
            {tab === 'chat' ? (
              <ChatPanel
                workspaceId={workspaceId}
                conversationId={conversationId}
                onConversationCreated={(id) => setConversationId(id)}
              />
            ) : !isRepoSelected || !selectedDoc ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                Select a GitHub repository document to view its {tab}.
              </div>
            ) : tab === 'overview' ? (
              <ArchitectureOverview documentId={selectedDoc.id} />
            ) : (
              <ArchitectureGraph documentId={selectedDoc.id} />
            )}
          </div>
        </section>
      </div>
    </Layout>
  )
}

function TabButton({
  active,
  disabled,
  onClick,
  children,
}: {
  active: boolean
  disabled?: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
        active
          ? 'border-indigo-500 text-indigo-300'
          : 'border-transparent text-slate-400 hover:text-slate-200'
      } ${disabled ? 'cursor-not-allowed opacity-40' : ''}`}
    >
      {children}
    </button>
  )
}
