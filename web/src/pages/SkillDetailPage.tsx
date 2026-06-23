import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSkill, saveSkillStructured, deleteSkill, validateSkill, listSkillFiles, readSkillFile } from '../api'
import { useToast } from '../components/Toast'
import FrontmatterForm from '../components/FrontmatterForm'
import ValidationPanel from '../components/ValidationPanel'
import FileTree from '../components/FileTree'
import type { ValidationResult, SkillFile } from '../types'

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

  const skillName = skill?.frontmatter?.name as string | undefined
  useEffect(() => {
    if (skill) {
      setFrontmatter(skill.frontmatter)
      setBody(skill.body)
      setDirty(false)
      setValidation(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skillName, name])

  const saveMutation = useMutation({
    mutationFn: () => saveSkillStructured(name!, frontmatter, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skill', name] })
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      setDirty(false)
      toast('Skill saved', 'success')
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
          <Link to="/" className="text-text-dim hover:text-text text-sm">&larr; Skills</Link>
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
            onClick={() => { if (confirm(`Delete skill '${name}'?`)) deleteMutation.mutate() }}
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
            <h3 className="text-xs font-medium text-text-dim uppercase tracking-wider mb-3">Body (Markdown)</h3>
            <textarea
              value={body}
              onChange={e => { setBody(e.target.value); setDirty(true) }}
              className="flex-1 w-full bg-bg-code border border-border rounded-lg p-4 text-sm text-text leading-relaxed resize-none focus:border-accent focus:outline-none min-h-64"
              spellCheck={false}
            />
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
            <ValidationPanel result={validation} loading={validating} />
            {!validation && !validating && (
              <p className="text-xs text-text-dim">Click "Validate" to check this skill.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
