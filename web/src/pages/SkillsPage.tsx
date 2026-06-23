import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listSkills, createSkill, addSkill } from '../api'
import { useToast } from '../components/Toast'
import SkillList from '../components/SkillList'

export default function SkillsPage() {
  const { data, isLoading } = useQuery({ queryKey: ['skills'], queryFn: listSkills })
  const [showCreate, setShowCreate] = useState(false)
  const [showAdd, setShowAdd] = useState(false)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Skills</h2>
          <p className="text-sm text-text-dim mt-1">
            {data ? `${data.skills.length} skill(s) across local and global scopes` : 'Loading...'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 text-sm font-medium bg-bg-card border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors"
          >
            Import Skill
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors"
          >
            New Skill
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-text-dim animate-pulse">Loading skills...</div>
      ) : (
        <SkillList skills={data?.skills || []} shadowed={data?.shadowed || []} />
      )}

      {showCreate && <CreateDialog onClose={() => setShowCreate(false)} />}
      {showAdd && <AddDialog onClose={() => setShowAdd(false)} />}
    </div>
  )
}

function CreateDialog({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [scope, setScope] = useState('global')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => createSkill(name, scope),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast(`Created skill '${data.name}'`, 'success')
      onClose()
      navigate(`/skills/${encodeURIComponent(data.name)}`)
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-4">New Skill</h3>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Skill Name</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="my-skill-name"
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-3"
        />
        <label className="block text-xs font-medium text-text-dim mb-1">Scope</label>
        <select
          value={scope}
          onChange={e => setScope(e.target.value)}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4"
        >
          <option value="global">Global</option>
          <option value="local">Local</option>
        </select>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function AddDialog({ onClose }: { onClose: () => void }) {
  const [path, setPath] = useState('')
  const [scope, setScope] = useState('global')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => addSkill(path, scope),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast(`Imported skill '${data.name}'`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-4">Import External Skill</h3>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Path to skill directory</label>
        <input
          type="text"
          value={path}
          onChange={e => setPath(e.target.value)}
          placeholder="/path/to/skill-dir"
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-3"
        />
        <label className="block text-xs font-medium text-text-dim mb-1">Scope</label>
        <select
          value={scope}
          onChange={e => setScope(e.target.value)}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4"
        >
          <option value="global">Global</option>
          <option value="local">Local</option>
        </select>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!path.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Importing...' : 'Import'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}
