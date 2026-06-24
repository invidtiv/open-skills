import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Skill, Category } from '../types'

interface Props {
  skills: Skill[]
  shadowed: string[]
  categories?: Category[]
  search?: string
  onMove?: (skill: Skill) => void
  onPromote?: (skill: Skill) => void
  onEditCategory?: (category: Category) => void
}

export default function SkillList({ skills, shadowed, categories = [], search = '', onMove, onPromote, onEditCategory }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const catMeta: Record<string, Category> = {}
  for (const c of categories) catMeta[c.name] = c

  const filtered = search
    ? skills.filter(s => {
        const q = search.toLowerCase()
        return (
          s.name.toLowerCase().includes(q) ||
          (s.description || '').toLowerCase().includes(q) ||
          (s.category || '').toLowerCase().includes(q) ||
          s.triggers.some(t => (typeof t === 'string' ? t : '').toLowerCase().includes(q))
        )
      })
    : skills

  if (filtered.length === 0) {
    return (
      <div className="text-center py-16 text-text-dim">
        {search ? (
          <>
            <p className="text-lg">No skills match "{search}"</p>
            <p className="text-sm mt-2">Try a different search term.</p>
          </>
        ) : (
          <>
            <p className="text-lg">No skills found.</p>
            <p className="text-sm mt-2">Create one to get started.</p>
          </>
        )}
      </div>
    )
  }

  const showCount = search && filtered.length !== skills.length

  const uncategorized = filtered.filter(s => !s.category)
  const byCategory: Record<string, Skill[]> = {}
  for (const s of filtered) {
    if (s.category) {
      ;(byCategory[s.category] ||= []).push(s)
    }
  }
  const catNames = Object.keys(byCategory).sort()

  const toggle = (cat: string) =>
    setCollapsed(prev => ({ ...prev, [cat]: !prev[cat] }))

  return (
    <div className="space-y-6">
      {showCount && (
        <p className="text-xs text-text-dim">
          Showing {filtered.length} of {skills.length} skills
        </p>
      )}
      {catNames.map(cat => (
        <div key={cat}>
          <div className="flex items-center gap-2 mb-1">
            <button
              onClick={() => toggle(cat)}
              className="flex items-center gap-2 text-left group"
            >
              <span className="text-xs text-text-dim transition-transform" style={{
                transform: collapsed[cat] ? 'rotate(-90deg)' : 'rotate(0deg)',
              }}>
                ▼
              </span>
              <h3 className="text-lg font-semibold text-text group-hover:text-accent transition-colors">
                {catMeta[cat]?.label || cat}
              </h3>
              <span className="text-xs text-text-dim font-mono bg-bg-code border border-border rounded px-2 py-0.5">
                {byCategory[cat].length}
              </span>
            </button>
            {onEditCategory && catMeta[cat] && (
              <button
                onClick={() => onEditCategory(catMeta[cat])}
                className="text-xs text-text-dim hover:text-accent transition-colors ml-1"
                title="Edit category"
              >
                ✎
              </button>
            )}
          </div>
          {catMeta[cat]?.description && !collapsed[cat] && (
            <p className="text-xs text-text-dim ml-5 mb-3">{catMeta[cat].description}</p>
          )}
          {!collapsed[cat] && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 ml-5">
              {byCategory[cat].map(s => (
                <SkillCard key={`${s.scope}-${s.name}`} skill={s} shadowed={shadowed} onMove={onMove} onPromote={onPromote} />
              ))}
            </div>
          )}
        </div>
      ))}

      {uncategorized.length > 0 && catNames.length > 0 && (
        <div>
          <button
            onClick={() => toggle('__uncategorized')}
            className="flex items-center gap-2 mb-3 text-left w-full group"
          >
            <span className="text-xs text-text-dim transition-transform" style={{
              transform: collapsed['__uncategorized'] ? 'rotate(-90deg)' : 'rotate(0deg)',
            }}>
              ▼
            </span>
            <h3 className="text-lg font-semibold text-text-dim group-hover:text-accent transition-colors">
              Uncategorized
            </h3>
            <span className="text-xs text-text-dim font-mono bg-bg-code border border-border rounded px-2 py-0.5">
              {uncategorized.length}
            </span>
          </button>
          {!collapsed['__uncategorized'] && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 ml-5">
              {uncategorized.map(s => (
                <SkillCard key={`${s.scope}-${s.name}`} skill={s} shadowed={shadowed} onMove={onMove} onPromote={onPromote} />
              ))}
            </div>
          )}
        </div>
      )}

      {uncategorized.length > 0 && catNames.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {uncategorized.map(s => (
            <SkillCard key={`${s.scope}-${s.name}`} skill={s} shadowed={shadowed} onMove={onMove} onPromote={onPromote} />
          ))}
        </div>
      )}
    </div>
  )
}

function SkillCard({ skill: s, shadowed, onMove, onPromote }: {
  skill: Skill; shadowed: string[]
  onMove?: (skill: Skill) => void
  onPromote?: (skill: Skill) => void
}) {
  return (
    <div className="p-5 bg-bg-card border border-border rounded-xl hover:border-accent transition-colors">
      <Link to={`/skills/${encodeURIComponent(s.name)}`}>
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-text truncate">{s.name}</h3>
          <span
            className={`shrink-0 text-xs font-mono px-2 py-0.5 rounded ${
              s.scope === 'Local'
                ? 'bg-green/15 text-green border border-green/30'
                : 'bg-accent/15 text-accent border border-accent/30'
            }`}
          >
            {s.scope}
          </span>
        </div>
        <p className="text-sm text-text-dim line-clamp-2 mb-3">{s.description || 'No description'}</p>
        {s.triggers.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {s.triggers.slice(0, 3).map((t, i) => (
              <span key={i} className="text-xs bg-bg-code border border-border rounded px-2 py-0.5 text-text-dim">
                {typeof t === 'string' ? t : JSON.stringify(t)}
              </span>
            ))}
            {s.triggers.length > 3 && (
              <span className="text-xs text-text-dim">+{s.triggers.length - 3}</span>
            )}
          </div>
        )}
        {shadowed.includes(s.name) && s.scope === 'Local' && (
          <p className="text-xs text-yellow mt-2">Shadows global</p>
        )}
      </Link>
      <div className="flex gap-2 mt-3 pt-3 border-t border-border">
        <button
          onClick={() => onMove?.(s)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-accent hover:border-accent transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
          </svg>
          Move
        </button>
        {s.scope === 'Local' && (
          <button
            onClick={() => onPromote?.(s)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-green/10 border border-green/30 rounded-lg text-green hover:bg-green/20 transition-colors ml-auto"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
            Promote
          </button>
        )}
      </div>
    </div>
  )
}
