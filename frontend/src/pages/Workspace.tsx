import { useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { MessageSquare, Network, ScrollText, type LucideIcon } from 'lucide-react'
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
    retry: 1,
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
          <div className="flex items-center gap-1 border-b border-white/5 px-4">
            <span className="mr-4 truncate py-3 text-sm font-semibold text-slate-200">
              {workspace?.name ?? 'Workspace'}
            </span>
            <TabButton icon={MessageSquare} active={tab === 'chat'} onClick={() => setTab('chat')}>
              Chat
            </TabButton>
            <TabButton
              icon={ScrollText}
              active={tab === 'overview'}
              disabled={!isRepoSelected}
              onClick={() => isRepoSelected && setTab('overview')}
            >
              Overview
            </TabButton>
            <TabButton
              icon={Network}
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
              <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-500">
                Select a GitHub repository document from the sidebar to view its {tab}.
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
  icon: Icon,
  active,
  disabled,
  onClick,
  children,
}: {
  icon: LucideIcon
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
      className={`relative flex items-center gap-1.5 px-3 py-3 text-sm font-medium transition-colors ${
        active ? 'text-indigo-300' : 'text-slate-400 hover:text-slate-200'
      } ${disabled ? 'cursor-not-allowed opacity-40 hover:text-slate-400' : ''}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {children}
      {active && (
        <motion.span
          layoutId="tab-underline"
          className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-brand-gradient"
        />
      )}
    </button>
  )
}
