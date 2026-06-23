import type { ValidationResult } from '../types'

interface Props {
  result: ValidationResult | null
  loading: boolean
}

export default function ValidationPanel({ result, loading }: Props) {
  if (loading) {
    return (
      <div className="p-4 text-sm text-text-dim animate-pulse">
        Running validation...
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="space-y-2">
      <div className={`text-sm font-medium px-3 py-2 rounded-lg ${
        result.valid
          ? 'bg-green/10 text-green border border-green/30'
          : 'bg-red/10 text-red border border-red/30'
      }`}>
        {result.valid ? 'Valid Open Skill' : `${result.errors.length} error(s) found`}
      </div>
      <div className="space-y-1">
        {result.checks.map((c, i) => (
          <div key={i} className="flex items-start gap-2 text-xs py-1">
            <span className={c.passed ? 'text-green' : 'text-red'}>
              {c.passed ? '[✓]' : '[✗]'}
            </span>
            <span className="text-text-dim">
              {c.label}
              {c.detail && <span className="text-text-dim/60 ml-1">— {c.detail}</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
