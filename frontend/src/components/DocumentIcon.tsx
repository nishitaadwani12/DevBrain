import {
  FileArchive,
  FileCode,
  FileText,
  FolderGit2,
  type LucideIcon,
} from 'lucide-react'
import type { DocumentSummary } from '../lib/types'

interface IconMeta {
  Icon: LucideIcon
  className: string
}

export function documentIconMeta(doc: DocumentSummary): IconMeta {
  if (doc.source_type === 'github') {
    return { Icon: FolderGit2, className: 'text-violet-300 bg-violet-500/15' }
  }
  if (doc.source_type === 'archive') {
    return { Icon: FileArchive, className: 'text-amber-300 bg-amber-500/15' }
  }
  const ext = doc.filename.split('.').pop()?.toLowerCase() ?? ''
  if (['md', 'markdown', 'txt', 'json', 'yaml', 'yml', 'ts', 'js', 'py'].includes(ext)) {
    return { Icon: FileCode, className: 'text-sky-300 bg-sky-500/15' }
  }
  return { Icon: FileText, className: 'text-indigo-300 bg-indigo-500/15' }
}

export default function DocumentIcon({
  doc,
  size = 16,
}: {
  doc: DocumentSummary
  size?: number
}) {
  const { Icon, className } = documentIconMeta(doc)
  return (
    <span
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${className}`}
    >
      <Icon size={size} />
    </span>
  )
}
