import { Link } from 'react-router-dom'
import type { Skill } from '../types'

interface Props {
  skills: Skill[]
  shadowed: string[]
}

export default function SkillList({ skills, shadowed }: Props) {
  if (skills.length === 0) {
    return (
      <div className="text-center py-16 text-text-dim">
        <p className="text-lg">No skills found.</p>
        <p className="text-sm mt-2">Create one to get started.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {skills.map(s => (
        <Link
          key={`${s.scope}-${s.name}`}
          to={`/skills/${encodeURIComponent(s.name)}`}
          className="block p-5 bg-bg-card border border-border rounded-xl hover:border-accent transition-colors"
        >
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
      ))}
    </div>
  )
}
