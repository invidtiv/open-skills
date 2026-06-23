import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listRunbooks, getRunbookState, startRunbook, advanceRunbook, prevRunbook, resetRunbook } from '../api'
import { useToast } from '../components/Toast'
import RunbookTracker from '../components/RunbookTracker'

export default function RunbooksPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: runbooksData } = useQuery({ queryKey: ['runbooks'], queryFn: listRunbooks })
  const { data: state } = useQuery({ queryKey: ['runbook-state'], queryFn: getRunbookState })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['runbook-state'] })
  }

  const startMutation = useMutation({
    mutationFn: startRunbook,
    onSuccess: (data) => { invalidate(); toast(data.message, 'success') },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const advanceMutation = useMutation({
    mutationFn: advanceRunbook,
    onSuccess: (data) => { invalidate(); toast(data.message, 'success') },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const prevMutation = useMutation({
    mutationFn: prevRunbook,
    onSuccess: (data) => { invalidate(); toast(data.message, 'success') },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const resetMutation = useMutation({
    mutationFn: resetRunbook,
    onSuccess: (data) => { invalidate(); toast(data.message, 'success') },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const loading = startMutation.isPending || advanceMutation.isPending || prevMutation.isPending || resetMutation.isPending

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-1">Runbooks</h2>
      <p className="text-sm text-text-dim mb-6">Chain skills together as multi-phase workflows.</p>

      {/* Available runbooks */}
      <div className="mb-8">
        <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Available</h3>
        {runbooksData?.runbooks.length === 0 && (
          <p className="text-sm text-text-dim">No runbooks found in local or global scope.</p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {runbooksData?.runbooks.map(rb => (
            <div key={`${rb.scope}-${rb.name}`} className="p-4 bg-bg-card border border-border rounded-xl">
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium">{rb.name}</h4>
                <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                  rb.scope === 'Local'
                    ? 'bg-green/15 text-green border border-green/30'
                    : 'bg-accent/15 text-accent border border-accent/30'
                }`}>
                  {rb.scope}
                </span>
              </div>
              <p className="text-xs text-text-dim mb-3">{rb.phase_count} phases</p>
              <button
                onClick={() => startMutation.mutate(rb.name)}
                disabled={loading}
                className="w-full px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
              >
                Start
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Active runbook */}
      <div>
        <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Active Runbook</h3>
        <RunbookTracker
          state={state || { active: false }}
          onAdvance={() => advanceMutation.mutate()}
          onPrev={() => prevMutation.mutate()}
          onReset={() => resetMutation.mutate()}
          loading={loading}
        />
      </div>
    </div>
  )
}
