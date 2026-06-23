import type { SkillFile } from '../types'

interface Props {
  files: SkillFile[]
  onSelect: (path: string) => void
  selected: string | null
}

export default function FileTree({ files, onSelect, selected }: Props) {
  if (files.length === 0) {
    return <p className="text-xs text-text-dim">No files</p>
  }

  return (
    <div className="space-y-0.5">
      {files.map(f => (
        <button
          key={f.path}
          onClick={() => onSelect(f.path)}
          className={`w-full text-left flex items-center gap-2 px-2 py-1 rounded text-xs font-mono transition-colors ${
            selected === f.path
              ? 'bg-accent/10 text-accent'
              : 'text-text-dim hover:text-text hover:bg-bg-code'
          }`}
        >
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span className="truncate">{f.path}</span>
          <span className="ml-auto text-text-dim/50">{formatSize(f.size)}</span>
        </button>
      ))}
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  return `${(bytes / 1024).toFixed(1)}K`
}
