import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listRunbooks, listSkills, getRunbookState, startRunbook, advanceRunbook, prevRunbook, resetRunbook, createRunbook, deleteRunbook } from '../api'
import { useToast } from '../components/Toast'
import RunbookTracker from '../components/RunbookTracker'
import type { Skill } from '../types'

interface PhaseRow {
  skill: string
  input: string
  output: string
}

function CreateRunbookDialog({ skills, onClose, onCreate }: {
  skills: Skill[]
  onClose: () => void
  onCreate: (name: string, scope: string, phases: PhaseRow[]) => void
}) {
  const [name, setName] = useState('')
  const [scope, setScope] = useState('local')
  const [phases, setPhases] = useState<PhaseRow[]>([{ skill: '', input: '', output: '' }])

  const updatePhase = (i: number, field: keyof PhaseRow, value: string) => {
    setPhases(prev => prev.map((p, idx) => idx === i ? { ...p, [field]: value } : p))
  }

  const addPhase = () => setPhases(prev => [...prev, { skill: '', input: '', output: '' }])

  const removePhase = (i: number) => {
    if (phases.length > 1) setPhases(prev => prev.filter((_, idx) => idx !== i))
  }

  const movePhase = (i: number, dir: -1 | 1) => {
    const j = i + dir
    if (j < 0 || j >= phases.length) return
    setPhases(prev => {
      const next = [...prev]
      ;[next[i], next[j]] = [next[j], next[i]]
      return next
    })
  }

  const valid = name.trim() && phases.every(p => p.skill)

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-bg-card border border-border rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-5 border-b border-border">
          <h3 className="text-lg font-semibold">Create Runbook</h3>
          <p className="text-xs text-text-dim mt-1">Chain skills together as a multi-phase workflow.</p>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-text-dim block mb-1">Name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. content-pipeline"
                className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm focus:border-accent focus:outline-none"
              />
            </div>
            <div className="w-32">
              <label className="text-xs text-text-dim block mb-1">Scope</label>
              <select
                value={scope}
                onChange={e => setScope(e.target.value)}
                className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm focus:border-accent focus:outline-none"
              >
                <option value="local">Local</option>
                <option value="global">Global</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-text-dim block mb-2">Phases</label>
            <div className="space-y-2">
              {phases.map((phase, i) => (
                <div key={i} className="flex items-start gap-2 p-3 bg-bg-code border border-border rounded-lg">
                  <span className="text-xs text-text-dim font-mono mt-2 w-6 shrink-0">{String(i + 1).padStart(2, '0')}</span>
                  <div className="flex-1 space-y-2">
                    <select
                      value={phase.skill}
                      onChange={e => updatePhase(i, 'skill', e.target.value)}
                      className="w-full bg-bg border border-border rounded px-2 py-1.5 text-sm focus:border-accent focus:outline-none"
                    >
                      <option value="">Select a skill...</option>
                      {skills.map(s => (
                        <option key={s.name} value={s.name}>{s.name}</option>
                      ))}
                    </select>
                    <div className="flex gap-2">
                      <input
                        value={phase.input}
                        onChange={e => updatePhase(i, 'input', e.target.value)}
                        placeholder="Input description"
                        className="flex-1 bg-bg border border-border rounded px-2 py-1.5 text-xs focus:border-accent focus:outline-none"
                      />
                      <input
                        value={phase.output}
                        onChange={e => updatePhase(i, 'output', e.target.value)}
                        placeholder="Expected output"
                        className="flex-1 bg-bg border border-border rounded px-2 py-1.5 text-xs focus:border-accent focus:outline-none"
                      />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1 shrink-0">
                    <button onClick={() => movePhase(i, -1)} disabled={i === 0} className="text-text-dim hover:text-text disabled:opacity-30 text-xs px-1">&#9650;</button>
                    <button onClick={() => movePhase(i, 1)} disabled={i === phases.length - 1} className="text-text-dim hover:text-text disabled:opacity-30 text-xs px-1">&#9660;</button>
                    <button onClick={() => removePhase(i)} disabled={phases.length <= 1} className="text-red hover:text-red/80 disabled:opacity-30 text-xs px-1">&#10005;</button>
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={addPhase}
              className="mt-2 text-xs text-accent hover:text-accent/80 font-medium"
            >
              + Add Phase
            </button>
          </div>
        </div>

        <div className="p-5 border-t border-border flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-dim hover:text-text border border-border rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={() => valid && onCreate(name.trim(), scope, phases)}
            disabled={!valid}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            Create Runbook
          </button>
        </div>
      </div>
    </div>
  )
}

export default function RunbooksPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [showCreate, setShowCreate] = useState(false)

  const { data: runbooksData } = useQuery({ queryKey: ['runbooks'], queryFn: listRunbooks })
  const { data: skillsData } = useQuery({ queryKey: ['skills'], queryFn: listSkills })
  const { data: state } = useQuery({ queryKey: ['runbook-state'], queryFn: getRunbookState })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['runbook-state'] })
    queryClient.invalidateQueries({ queryKey: ['runbooks'] })
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

  const createMutation = useMutation({
    mutationFn: ({ name, scope, phases }: { name: string; scope: string; phases: PhaseRow[] }) =>
      createRunbook(name, scope, phases),
    onSuccess: () => {
      invalidate()
      setShowCreate(false)
      toast('Runbook created', 'success')
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRunbook,
    onSuccess: () => { invalidate(); toast('Runbook deleted', 'success') },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const loading = startMutation.isPending || advanceMutation.isPending || prevMutation.isPending || resetMutation.isPending

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-2xl font-bold">Runbooks</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors"
        >
          + Create Runbook
        </button>
      </div>
      <p className="text-sm text-text-dim mb-6">Chain skills together as multi-phase workflows.</p>

      {/* Available runbooks */}
      <div className="mb-8">
        <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Available</h3>
        {runbooksData?.runbooks.length === 0 && (
          <p className="text-sm text-text-dim">No runbooks yet. Create one to chain skills together.</p>
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
              <div className="flex gap-2">
                <button
                  onClick={() => startMutation.mutate(rb.name)}
                  disabled={loading}
                  className="flex-1 px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
                >
                  Start
                </button>
                <button
                  onClick={() => { if (confirm(`Delete runbook '${rb.name}'?`)) deleteMutation.mutate(rb.name) }}
                  className="px-3 py-1.5 text-xs font-medium bg-red/10 border border-red/30 rounded-lg text-red hover:bg-red/20 transition-colors"
                >
                  Delete
                </button>
              </div>
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

      {showCreate && skillsData && (
        <CreateRunbookDialog
          skills={skillsData.skills}
          onClose={() => setShowCreate(false)}
          onCreate={(name, scope, phases) => createMutation.mutate({ name, scope, phases })}
        />
      )}
    </div>
  )
}
