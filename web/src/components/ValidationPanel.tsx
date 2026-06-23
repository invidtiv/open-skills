import { useState } from 'react'
import type { ValidationResult } from '../types'

interface SuggestFixResult {
  suggestion: string
  frontmatter: Record<string, unknown>
  body: string
}

interface Props {
  result: ValidationResult | null
  loading: boolean
  onSuggestFix?: () => Promise<SuggestFixResult | null>
  onApplyFix?: (frontmatter: Record<string, unknown>, body: string) => void
}

export default function ValidationPanel({ result, loading, onSuggestFix, onApplyFix }: Props) {
  const [suggesting, setSuggesting] = useState(false)
  const [fixResult, setFixResult] = useState<SuggestFixResult | null>(null)

  if (loading) {
    return (
      <div className="p-4 text-sm text-text-dim animate-pulse">
        Running validation...
      </div>
    )
  }

  if (!result) return null

  const handleSuggestFix = async () => {
    if (!onSuggestFix) return
    setSuggesting(true)
    setFixResult(null)
    try {
      const res = await onSuggestFix()
      setFixResult(res)
    } finally {
      setSuggesting(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className={`text-sm font-medium px-3 py-2 rounded-lg ${
        result.valid
          ? 'bg-green/10 text-green border border-green/30'
          : 'bg-red/10 text-red border border-red/30'
      }`}>
        {result.valid ? 'Valid Open Skill' : `${result.errors.length} error(s) found`}
      </div>
      {result.warnings && result.warnings.length > 0 && (
        <div className="text-xs text-yellow px-3 py-2 bg-yellow/10 border border-yellow/30 rounded-lg space-y-1">
          {result.warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      )}
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

      {!result.valid && onSuggestFix && (
        <div className="pt-2 space-y-2">
          <button
            onClick={handleSuggestFix}
            disabled={suggesting}
            className="w-full px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
          >
            {suggesting ? 'Asking DeepSeek...' : 'Suggest Fix'}
          </button>

          {fixResult && (
            <div className="space-y-2">
              <p className="text-xs text-text-dim font-medium">Suggested fix:</p>
              <pre className="text-xs bg-bg-code border border-border rounded-lg p-3 overflow-x-auto max-h-64 text-text-dim whitespace-pre-wrap">
                {fixResult.suggestion}
              </pre>
              {onApplyFix && (
                <button
                  onClick={() => onApplyFix(fixResult.frontmatter, fixResult.body)}
                  className="w-full px-3 py-1.5 text-xs font-medium bg-green/10 border border-green/30 rounded-lg text-green hover:bg-green/20 transition-colors"
                >
                  Apply Fix
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
