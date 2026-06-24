import { useState, useEffect, type ReactNode } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSkill, saveSkillStructured, deleteSkill, validateSkill, suggestFix, listSkillFiles, readSkillFile } from '../api'
import { useToast } from '../components/Toast'
import FrontmatterForm from '../components/FrontmatterForm'
import ValidationPanel from '../components/ValidationPanel'
import FileTree from '../components/FileTree'
import type { ValidationResult, SkillFile } from '../types'

// Lightweight markdown-to-JSX renderer for the body preview. Intentionally
// simple — handles headings, lists, checkboxes, fenced code, and paragraphs.
function renderMarkdown(md: string): ReactNode[] {
  const lines = md.split('\n')
  const elements: ReactNode[] = []
  let listItems: ReactNode[] = []
  let paraLines: string[] = []
  let key = 0
  let i = 0

  const flushList = () => {
    if (listItems.length) {
      elements.push(
        <ul key={key++} className="my-2 pl-5 space-y-1">{listItems}</ul>
      )
      listItems = []
    }
  }
  const flushPara = () => {
    if (paraLines.length) {
      elements.push(
        <p key={key++} className="my-2 text-sm text-text leading-relaxed">{paraLines.join(' ')}</p>
      )
      paraLines = []
    }
  }

  while (i < lines.length) {
    const line = lines[i]

    // Fenced code block
    if (line.trim().startsWith('```')) {
      flushPara(); flushList()
      const code: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        code.push(lines[i]); i++
      }
      i++ // skip closing fence
      elements.push(
        <pre key={key++} className="my-2 bg-bg-code border border-border rounded-lg p-3 text-xs text-text-dim overflow-x-auto">{code.join('\n')}</pre>
      )
      continue
    }

    // Headings (# .. ####)
    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      flushPara(); flushList()
      const level = heading[1].length
      const Tag = (`h${level}`) as 'h1' | 'h2' | 'h3' | 'h4'
      const sizeCls = level === 1 ? 'text-xl' : level === 2 ? 'text-lg' : level === 3 ? 'text-base' : 'text-sm'
      elements.push(
        <Tag key={key++} className={`${sizeCls} font-semibold text-text mt-4 mb-2`}>{heading[2]}</Tag>
      )
      i++
      continue
    }

    // List items + checkboxes
    const listMatch = line.match(/^\s*-\s+(.*)$/)
    if (listMatch) {
      flushPara()
      const content = listMatch[1]
      const checkbox = content.match(/^\[([ xX])\]\s+(.*)$/)
      if (checkbox) {
        const checked = checkbox[1].toLowerCase() === 'x'
        listItems.push(
          <li key={key++} className="list-none -ml-5 flex items-center gap-2 text-sm text-text">
            <input type="checkbox" checked={checked} readOnly className="accent-accent" />
            <span className={checked ? 'text-text-dim line-through' : ''}>{checkbox[2]}</span>
          </li>
        )
      } else {
        listItems.push(
          <li key={key++} className="list-disc text-sm text-text">{content}</li>
        )
      }
      i++
      continue
    }

    // Blank line — paragraph/list boundary
    if (line.trim() === '') {
      flushPara(); flushList()
      i++
      continue
    }

    // Regular paragraph text
    flushList()
    paraLines.push(line)
    i++
  }

  flushPara(); flushList()
  return elements
}

export default function SkillDetailPage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: skill, isLoading } = useQuery({
    queryKey: ['skill', name],
    queryFn: () => getSkill(name!),
    enabled: !!name,
  })

  const { data: filesData } = useQuery({
    queryKey: ['skill-files', name],
    queryFn: () => listSkillFiles(name!),
    enabled: !!name,
  })

  const [frontmatter, setFrontmatter] = useState<Record<string, unknown>>({})
  const [body, setBody] = useState('')
  const [dirty, setDirty] = useState(false)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [validating, setValidating] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [bodyTab, setBodyTab] = useState<'edit' | 'preview'>('edit')

  const skillName = skill?.frontmatter?.name as string | undefined
  useEffect(() => {
    if (skill) {
      setFrontmatter(skill.frontmatter)
      setBody(skill.body)
      setDirty(false)
      setValidation(null)
      setBodyTab('edit')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skillName, name])

  // Warn on browser close/refresh while there are unsaved changes.
  useEffect(() => {
    if (!dirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  const handleValidate = async () => {
    if (!name) return
    setValidating(true)
    try {
      const result = await validateSkill(name)
      setValidation(result)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Validation failed', 'error')
    } finally {
      setValidating(false)
    }
  }

  const saveMutation = useMutation({
    mutationFn: () => saveSkillStructured(name!, frontmatter, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill', name] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      setDirty(false)
      toast('Skill saved', 'success')
      // If validation was already run, re-run it so stale errors don't linger.
      if (validation !== null) handleValidate()
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteSkill(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast('Skill deleted', 'success')
      navigate('/')
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const handleBack = () => {
    if (dirty && !confirm('You have unsaved changes. Leave without saving?')) return
    navigate('/')
  }

  const handleSuggestFix = async () => {
    if (!name || !validation) return null
    try {
      return await suggestFix(name, validation.errors, validation.warnings)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to get suggestion', 'error')
      return null
    }
  }

  const handleApplyFix = (fm: Record<string, unknown>, b: string) => {
    setFrontmatter(fm)
    setBody(b)
    setDirty(true)
    setValidation(null)
    toast('Fix applied — review and save when ready', 'success')
  }

  const handleFileSelect = async (path: string) => {
    if (!name) return
    setSelectedFile(path)
    try {
      const data = await readSkillFile(name, path)
      setFileContent(data.content)
    } catch {
      setFileContent(null)
    }
  }

  if (isLoading) {
    return <div className="p-6 text-text-dim animate-pulse">Loading skill...</div>
  }

  if (!skill) {
    return (
      <div className="p-6 text-center">
        <p className="text-text-dim">Skill not found.</p>
        <Link to="/" className="text-accent text-sm mt-2 inline-block">Back to skills</Link>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-bg-card">
        <div className="flex items-center gap-3">
          <button onClick={handleBack} className="text-text-dim hover:text-text text-sm">&larr; Skills</button>
          <span className="text-border">/</span>
          <h2 className="font-semibold">{skill.frontmatter.name as string || name}</h2>
          <span className={`text-xs font-mono px-2 py-0.5 rounded ${
            skill.scope === 'Local'
              ? 'bg-green/15 text-green border border-green/30'
              : 'bg-accent/15 text-accent border border-accent/30'
          }`}>
            {skill.scope}
          </span>
          {dirty && <span className="text-xs text-yellow">unsaved</span>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleValidate}
            disabled={validating}
            className="px-3 py-1.5 text-xs font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors disabled:opacity-50"
          >
            Validate
          </button>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !dirty}
            className="px-3 py-1.5 text-xs font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-3 py-1.5 text-xs font-medium bg-red/10 border border-red/30 rounded-lg text-red hover:bg-red/20 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Editor area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: frontmatter form + body editor */}
        <div className="flex-[3] flex flex-col overflow-y-auto border-r border-border">
          <div className="p-5 border-b border-border">
            <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Frontmatter</h3>
            <FrontmatterForm
              frontmatter={frontmatter}
              onChange={fm => { setFrontmatter(fm); setDirty(true) }}
            />
          </div>
          <div className="flex-1 flex flex-col p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider">Body (Markdown)</h3>
              <div className="flex gap-1 bg-bg-code border border-border rounded-lg p-0.5">
                <button
                  onClick={() => setBodyTab('edit')}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    bodyTab === 'edit' ? 'bg-accent/15 text-accent' : 'text-text-dim hover:text-text'
                  }`}
                >
                  Edit
                </button>
                <button
                  onClick={() => setBodyTab('preview')}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    bodyTab === 'preview' ? 'bg-accent/15 text-accent' : 'text-text-dim hover:text-text'
                  }`}
                >
                  Preview
                </button>
              </div>
            </div>
            {bodyTab === 'edit' ? (
              <textarea
                value={body}
                onChange={e => { setBody(e.target.value); setDirty(true) }}
                className="flex-1 w-full bg-bg-code border border-border rounded-lg p-4 text-sm text-text leading-relaxed resize-none focus:border-accent focus:outline-none min-h-64"
                spellCheck={false}
              />
            ) : (
              <div className="prose flex-1 w-full bg-bg-code border border-border rounded-lg p-4 overflow-y-auto min-h-64 text-text">
                {body.trim()
                  ? renderMarkdown(body)
                  : <p className="text-sm text-text-dim">Nothing to preview.</p>}
              </div>
            )}
          </div>
        </div>

        {/* Right: file tree + validation */}
        <div className="flex-[2] flex flex-col overflow-y-auto max-w-md">
          <div className="p-5 border-b border-border">
            <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Files</h3>
            <FileTree
              files={(filesData?.files || []) as SkillFile[]}
              onSelect={handleFileSelect}
              selected={selectedFile}
            />
            {fileContent !== null && selectedFile && (
              <div className="mt-3">
                <p className="text-xs text-text-dim font-mono mb-1">{selectedFile}</p>
                <pre className="text-xs bg-bg-code border border-border rounded-lg p-3 overflow-x-auto max-h-48 text-text-dim">
                  {fileContent}
                </pre>
              </div>
            )}
          </div>
          <div className="p-5">
            <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Validation</h3>
            <ValidationPanel
              result={validation}
              loading={validating}
              onSuggestFix={handleSuggestFix}
              onApplyFix={handleApplyFix}
            />
            {!validation && !validating && (
              <p className="text-xs text-text-dim">Click "Validate" to check this skill.</p>
            )}
          </div>
        </div>
      </div>

      {/* Themed delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-sm mx-4 bg-bg-card border border-border rounded-lg p-5 shadow-xl">
            <h3 className="text-sm font-semibold text-text mb-2">Delete skill</h3>
            <p className="text-sm text-text-dim mb-5">
              Are you sure you want to delete{' '}
              <span className="font-mono text-text">{skill.frontmatter.name as string || name}</span>?
              This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3 py-1.5 text-xs font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowDeleteConfirm(false); deleteMutation.mutate() }}
                disabled={deleteMutation.isPending}
                className="px-3 py-1.5 text-xs font-medium bg-red/10 border border-red/30 rounded-lg text-red hover:bg-red/20 transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
