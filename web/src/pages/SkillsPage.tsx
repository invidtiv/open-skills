import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  listSkills, createSkill, addSkill, importGithub,
  listCategories, moveSkill, promoteSkill, createCategory, updateCategory,
  getGitStatus, gitPush,
} from '../api'
import type { GitStatus } from '../api'
import { useToast } from '../components/Toast'
import SkillList from '../components/SkillList'
import type { Skill, Category } from '../types'

export default function SkillsPage() {
  const { data, isLoading } = useQuery({ queryKey: ['skills'], queryFn: listSkills })
  const { data: catData } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: gitData } = useQuery({ queryKey: ['git-status'], queryFn: getGitStatus, refetchInterval: 30000 })
  const [showCreate, setShowCreate] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [showGithub, setShowGithub] = useState(false)
  const [showNewCategory, setShowNewCategory] = useState(false)
  const [moveTarget, setMoveTarget] = useState<Skill | null>(null)
  const [promoteTarget, setPromoteTarget] = useState<Skill | null>(null)
  const [editCat, setEditCat] = useState<Category | null>(null)
  const [search, setSearch] = useState('')
  const [showSync, setShowSync] = useState(false)
  const [showActions, setShowActions] = useState(false)
  const [filter, setFilter] = useState<'all' | 'pending'>('all')

  const categories = catData?.categories || []

  const displaySkills = filter === 'pending'
    ? (data?.skills || []).filter(s => s.scope === 'Local' && (s.category === 'pending-review' || !s.category))
    : (data?.skills || [])

  const pendingCount = (data?.skills || []).filter(s => s.scope === 'Local' && (s.category === 'pending-review' || !s.category)).length

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold">Skills</h2>
          <p className="text-sm text-text-dim mt-1">
            {data ? `${data.skills.length} skill(s) in ${categories.length} categories` : 'Loading...'}
          </p>
        </div>
        <div className="flex gap-2">
          {gitData?.initialized && (
            <button
              onClick={() => setShowSync(true)}
              className={`px-4 py-2 text-sm font-medium border rounded-lg transition-colors ${
                gitData.clean
                  ? 'bg-bg-card border-border text-text-dim hover:text-text hover:border-accent'
                  : 'bg-yellow/10 border-yellow/30 text-yellow hover:bg-yellow/20'
              }`}
            >
              {gitData.clean ? 'Synced' : `${gitData.changed_files} change(s)`}
            </button>
          )}
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors"
          >
            New Skill
          </button>
          <div className="relative">
            <button
              onClick={() => setShowActions(v => !v)}
              className="px-3 py-2 text-sm font-medium bg-bg-card border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors"
              aria-label="More actions"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
              </svg>
            </button>
            {showActions && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setShowActions(false)} />
                <div className="absolute right-0 top-full mt-1 z-40 w-48 bg-bg-card border border-border rounded-lg shadow-xl py-1">
                  <button
                    onClick={() => { setShowNewCategory(true); setShowActions(false) }}
                    className="w-full text-left px-4 py-2 text-sm text-text-dim hover:text-text hover:bg-bg-code transition-colors"
                  >
                    New Category
                  </button>
                  <button
                    onClick={() => { setShowGithub(true); setShowActions(false) }}
                    className="w-full text-left px-4 py-2 text-sm text-text-dim hover:text-text hover:bg-bg-code transition-colors"
                  >
                    Import from GitHub
                  </button>
                  <button
                    onClick={() => { setShowAdd(true); setShowActions(false) }}
                    className="w-full text-left px-4 py-2 text-sm text-text-dim hover:text-text hover:bg-bg-code transition-colors"
                  >
                    Import Local
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-3 mb-4 items-center">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search skills by name, description, category, or trigger..."
          className="flex-1 bg-bg-code border border-border rounded-lg px-4 py-2.5 text-sm text-text placeholder:text-text-dim/50 focus:border-accent focus:outline-none"
        />
        <div className="flex shrink-0 bg-bg-code border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              filter === 'all' ? 'bg-accent/15 text-accent' : 'text-text-dim hover:text-text'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              filter === 'pending' ? 'bg-yellow/15 text-yellow' : 'text-text-dim hover:text-text'
            }`}
          >
            Pending{pendingCount > 0 ? ` (${pendingCount})` : ''}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-text-dim animate-pulse">Loading skills...</div>
      ) : (
        <SkillList
          skills={displaySkills}
          shadowed={data?.shadowed || []}
          categories={categories}
          search={search}
          onMove={setMoveTarget}
          onPromote={setPromoteTarget}
          onEditCategory={setEditCat}
        />
      )}

      {showCreate && <CreateDialog onClose={() => setShowCreate(false)} />}
      {showAdd && <AddDialog onClose={() => setShowAdd(false)} />}
      {showGithub && <GithubDialog onClose={() => setShowGithub(false)} />}
      {showNewCategory && <NewCategoryDialog onClose={() => setShowNewCategory(false)} />}
      {moveTarget && <MoveDialog skill={moveTarget} categories={categories} onClose={() => setMoveTarget(null)} />}
      {promoteTarget && <PromoteDialog skill={promoteTarget} categories={categories} onClose={() => setPromoteTarget(null)} />}
      {editCat && <EditCategoryDialog category={editCat} onClose={() => setEditCat(null)} />}
      {showSync && gitData && <SyncDialog gitStatus={gitData} onClose={() => setShowSync(false)} />}
    </div>
  )
}

function EditCategoryDialog({ category, onClose }: { category: Category; onClose: () => void }) {
  const [name, setName] = useState(category.label || category.name)
  const [description, setDescription] = useState(category.description)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => updateCategory(category.name, name !== category.name ? name : '', description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast(`Updated category '${name}'`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-4">Edit Category</h3>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Name</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-3"
        />
        <label className="block text-xs font-medium text-text-dim mb-1">Description</label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={3}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4 resize-none"
        />
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Cancel</button>
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function MoveDialog({ skill, categories, onClose }: { skill: Skill; categories: Category[]; onClose: () => void }) {
  const [category, setCategory] = useState('')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => moveSkill(skill.name, category, skill.scope.toLowerCase()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast(`Moved '${skill.name}' to ${category}`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-1">Move Skill</h3>
      <p className="text-xs text-text-dim mb-4">Move <span className="font-mono text-text">{skill.name}</span> to a different category.</p>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Target Category</label>
        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4"
        >
          <option value="">Select a category...</option>
          {categories.map(c => (
            <option key={c.name} value={c.name}>{c.name} ({c.skill_count} skills)</option>
          ))}
        </select>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Cancel</button>
          <button
            type="submit"
            disabled={!category || mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Moving...' : 'Move'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function PromoteDialog({ skill, categories, onClose }: { skill: Skill; categories: Category[]; onClose: () => void }) {
  const [category, setCategory] = useState('')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => promoteSkill(skill.name, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast(`Promoted '${skill.name}' to global`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const globalCategories = categories.filter(c => c.scope === 'Global')

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-1">Approve & Promote to Global</h3>
      <p className="text-xs text-text-dim mb-4">
        Move <span className="font-mono text-text">{skill.name}</span> from local to global scope.
        Optionally place it in a category.
      </p>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Category (optional)</label>
        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4"
        >
          <option value="">Uncategorized</option>
          {globalCategories.map(c => (
            <option key={c.name} value={c.name}>{c.name} ({c.skill_count} skills)</option>
          ))}
        </select>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Cancel</button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-green/10 border border-green/30 rounded-lg text-green hover:bg-green/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Promoting...' : 'Promote to Global'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function NewCategoryDialog({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [scope, setScope] = useState('global')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => createCategory(name, description, scope),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast(`Created category '${data.name}'`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-4">New Category</h3>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Category Name</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="my-category"
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-3"
        />
        <label className="block text-xs font-medium text-text-dim mb-1">Description</label>
        <input
          type="text"
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="What this category is for"
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
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Cancel</button>
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

function GithubDialog({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState('')
  const [scope, setScope] = useState('global')
  const [subdir, setSubdir] = useState('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => importGithub(url, scope, subdir),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast(`Imported '${data.name}' from GitHub`, 'success')
      onClose()
      navigate(`/skills/${encodeURIComponent(data.name)}`)
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-1">Import from GitHub</h3>
      <p className="text-xs text-text-dim mb-4">Clone a skill directly from a GitHub repository.</p>
      <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
        <label className="block text-xs font-medium text-text-dim mb-1">Repository URL</label>
        <input
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo or owner/repo"
          autoFocus
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-3"
        />
        <label className="block text-xs font-medium text-text-dim mb-1">Subdirectory (optional)</label>
        <input
          type="text"
          value={subdir}
          onChange={e => setSubdir(e.target.value)}
          placeholder="e.g. skills/my-skill"
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
            disabled={!url.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
          >
            {mutation.isPending ? 'Cloning...' : 'Import'}
          </button>
        </div>
      </form>
    </Overlay>
  )
}

function SyncDialog({ gitStatus: gs, onClose }: { gitStatus: GitStatus; onClose: () => void }) {
  const [message, setMessage] = useState('')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: () => gitPush(message || `Update ${gs.changed_files} file(s)`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['git-status'] })
      toast(data.action === 'nothing' ? 'Nothing to push' : `Pushed ${data.commit} (${data.files} files)`, 'success')
      onClose()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <Overlay onClose={onClose}>
      <h3 className="text-lg font-semibold mb-4">Git Sync</h3>

      <div className="space-y-2 mb-4 text-sm">
        <div className="flex justify-between">
          <span className="text-text-dim">Status</span>
          <span className={gs.clean ? 'text-green' : 'text-yellow'}>
            {gs.clean ? 'Clean' : `${gs.changed_files} changed file(s)`}
          </span>
        </div>
        {gs.last_commit && (
          <div className="flex justify-between">
            <span className="text-text-dim">Last commit</span>
            <span className="text-text font-mono text-xs">{gs.last_commit}</span>
          </div>
        )}
        {gs.remote && (
          <div className="flex justify-between">
            <span className="text-text-dim">Remote</span>
            <span className="text-text text-xs truncate ml-4">{gs.remote}</span>
          </div>
        )}
      </div>

      {!gs.clean && gs.changes && gs.changes.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-text-dim mb-1">Changes</p>
          <div className="bg-bg-code border border-border rounded-lg p-2 max-h-40 overflow-y-auto">
            {gs.changes.map((c, i) => (
              <div key={i} className="text-xs font-mono text-text-dim">{c}</div>
            ))}
          </div>
        </div>
      )}

      {!gs.clean && (
        <form onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
          <label className="block text-xs font-medium text-text-dim mb-1">Commit message (optional)</label>
          <input
            type="text"
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder={`Update ${gs.changed_files} file(s)`}
            className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none mb-4"
          />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Cancel</button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-green/10 border border-green/30 rounded-lg text-green hover:bg-green/20 disabled:opacity-50"
            >
              {mutation.isPending ? 'Pushing...' : 'Commit & Push'}
            </button>
          </div>
        </form>
      )}

      {gs.clean && (
        <div className="flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-text-dim hover:text-text">Close</button>
        </div>
      )}
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
