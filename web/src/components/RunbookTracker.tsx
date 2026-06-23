import type { RunbookState } from '../types'

interface Props {
  state: RunbookState
  onAdvance: () => void
  onPrev: () => void
  onReset: () => void
  loading: boolean
}

export default function RunbookTracker({ state, onAdvance, onPrev, onReset, loading }: Props) {
  if (!state.active || !state.phases) {
    return (
      <div className="text-center py-8 text-text-dim">
        <p>No active runbook.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-text">{state.runbook}</h3>
          {state.updated_at && (
            <p className="text-xs text-text-dim mt-0.5">
              Updated: {new Date(state.updated_at).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={onPrev}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={onAdvance}
            disabled={loading || state.current_phase === null}
            className="px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
          >
            Next
          </button>
          <button
            onClick={onReset}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-medium bg-red/10 border border-red/30 rounded-lg text-red hover:bg-red/20 transition-colors disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg-card text-text-dim text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-2.5 w-16">Phase</th>
              <th className="text-left px-4 py-2.5">Skill</th>
              <th className="text-left px-4 py-2.5">Input</th>
              <th className="text-left px-4 py-2.5">Output</th>
              <th className="text-left px-4 py-2.5 w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            {state.phases.map(p => {
              const isActive = p.phase === state.current_phase
              return (
                <tr
                  key={p.phase}
                  className={`border-t border-border ${isActive ? 'bg-accent/5' : ''}`}
                >
                  <td className="px-4 py-2.5 font-mono">
                    {isActive && <span className="text-accent mr-1">&#9654;</span>}
                    {p.phase}
                  </td>
                  <td className="px-4 py-2.5 font-medium">{p.skill}</td>
                  <td className="px-4 py-2.5 text-text-dim">{p.input}</td>
                  <td className="px-4 py-2.5 text-text-dim">{p.output}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={isActive ? 'active' : p.status} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-accent/15 text-accent border-accent/30',
    completed: 'bg-green/15 text-green border-green/30',
    pending: 'bg-bg-code text-text-dim border-border',
  }

  return (
    <span className={`inline-block text-xs font-mono px-2 py-0.5 rounded border ${colors[status] || colors.pending}`}>
      {status}
    </span>
  )
}
