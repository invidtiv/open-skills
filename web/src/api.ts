import type { Skill, SkillDetail, SkillFile, ValidationResult, Runbook, RunbookState, Agent, AgentActionResponse, RecommendResult, Category } from './types'

const BASE = '/api'

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {}
  if (opts?.body) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { ...headers, ...(opts?.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || res.statusText)
  }
  return res.json()
}

export async function listSkills(): Promise<{ skills: Skill[]; shadowed: string[] }> {
  return request('/skills')
}

export async function getSkill(name: string): Promise<SkillDetail> {
  return request(`/skills/${encodeURIComponent(name)}`)
}

export async function createSkill(name: string, scope: string): Promise<{ name: string; path: string }> {
  return request('/skills', { method: 'POST', body: JSON.stringify({ name, scope }) })
}

export async function saveSkill(name: string, content: string): Promise<{ saved: boolean }> {
  return request(`/skills/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify({ content }) })
}

export async function saveSkillStructured(name: string, frontmatter: Record<string, unknown>, body: string): Promise<{ saved: boolean; name: string }> {
  return request(`/skills/${encodeURIComponent(name)}/structured`, { method: 'PUT', body: JSON.stringify({ frontmatter, body }) })
}

export async function deleteSkill(name: string): Promise<{ deleted: boolean }> {
  return request(`/skills/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export async function validateSkill(name: string): Promise<ValidationResult> {
  return request(`/skills/${encodeURIComponent(name)}/validate`, { method: 'POST' })
}

export async function suggestFix(name: string, errors: string[], warnings: string[]): Promise<{ suggestion: string; frontmatter: Record<string, unknown>; body: string }> {
  return request(`/skills/${encodeURIComponent(name)}/suggest-fix`, {
    method: 'POST',
    body: JSON.stringify({ errors, warnings }),
  })
}

export async function addSkill(path: string, scope: string): Promise<{ name: string }> {
  return request('/skills/add', { method: 'POST', body: JSON.stringify({ path, scope }) })
}

export async function importGithub(url: string, scope: string, subdir?: string): Promise<{ name: string; source: string }> {
  return request('/skills/import-github', { method: 'POST', body: JSON.stringify({ url, scope, subdir: subdir || '' }) })
}

export async function extractSkill(): Promise<{ name: string; path: string }> {
  return request('/skills/extract', { method: 'POST' })
}

export async function listSkillFiles(name: string): Promise<{ files: SkillFile[] }> {
  return request(`/skills/${encodeURIComponent(name)}/files`)
}

export async function readSkillFile(name: string, filepath: string): Promise<{ content: string }> {
  const encodedPath = filepath.split('/').map(encodeURIComponent).join('/')
  return request(`/skills/${encodeURIComponent(name)}/files/${encodedPath}`)
}

export async function listRunbooks(): Promise<{ runbooks: Runbook[] }> {
  return request('/runbooks')
}

export async function getRunbookState(): Promise<RunbookState> {
  return request('/runbooks/state')
}

export async function startRunbook(name: string): Promise<{ message: string }> {
  return request(`/runbooks/${encodeURIComponent(name)}/start`, { method: 'POST' })
}

export async function advanceRunbook(): Promise<{ message: string }> {
  return request('/runbooks/advance', { method: 'POST' })
}

export async function prevRunbook(): Promise<{ message: string }> {
  return request('/runbooks/prev', { method: 'POST' })
}

export async function resetRunbook(): Promise<{ message: string }> {
  return request('/runbooks/reset', { method: 'POST' })
}

export async function createRunbook(name: string, scope: string, phases: { skill: string; input: string; output: string }[]): Promise<{ name: string }> {
  return request('/runbooks', { method: 'POST', body: JSON.stringify({ name, scope, phases }) })
}

export async function deleteRunbook(name: string): Promise<{ deleted: boolean }> {
  return request(`/runbooks/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

export async function listAgents(): Promise<{ agents: Agent[] }> {
  return request('/agents')
}

export async function connectAgent(agentId: string, scope: string = 'all', dryRun: boolean = false): Promise<AgentActionResponse> {
  return request(`/agents/${encodeURIComponent(agentId)}/connect`, {
    method: 'POST',
    body: JSON.stringify({ scope, dryRun }),
  })
}

export async function disconnectAgent(agentId: string): Promise<AgentActionResponse> {
  return request(`/agents/${encodeURIComponent(agentId)}/disconnect`, { method: 'POST' })
}

export async function customConnectAgent(configPath: string, format: string = 'mcp-json', scope: string = 'all', dryRun: boolean = false): Promise<AgentActionResponse> {
  return request('/agents/custom/connect', {
    method: 'POST',
    body: JSON.stringify({ configPath, format, scope, dryRun }),
  })
}

export async function recommendSkills(query: string, limit: number = 5, scope: string = 'all'): Promise<RecommendResult> {
  return request('/skills/recommend', {
    method: 'POST',
    body: JSON.stringify({ query, limit, scope }),
  })
}

export async function listCategories(): Promise<{ categories: Category[] }> {
  return request('/categories')
}

export async function moveSkill(name: string, category: string, scope: string = 'global'): Promise<{ action: string }> {
  return request(`/skills/${encodeURIComponent(name)}/move`, {
    method: 'POST',
    body: JSON.stringify({ category, scope }),
  })
}

export async function promoteSkill(name: string, category: string = ''): Promise<{ action: string }> {
  return request(`/skills/${encodeURIComponent(name)}/promote`, {
    method: 'POST',
    body: JSON.stringify({ category }),
  })
}

export async function createCategory(name: string, description: string = '', scope: string = 'global'): Promise<{ action: string; name: string }> {
  return request('/categories', {
    method: 'POST',
    body: JSON.stringify({ name, description, scope }),
  })
}

export async function updateCategory(name: string, newName: string = '', description?: string): Promise<{ action: string; name: string }> {
  return request(`/categories/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify({ new_name: newName, description }),
  })
}

export interface GitStatus {
  initialized: boolean
  clean?: boolean
  changed_files?: number
  changes?: string[]
  remote?: string | null
  last_commit?: string | null
  ahead?: number
  error?: string
}

export async function getGitStatus(): Promise<GitStatus> {
  return request('/git/status')
}

export async function gitPush(message: string = ''): Promise<{ action: string; commit?: string; files?: number; message?: string }> {
  return request('/git/push', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export interface TriggerMatch {
  skill: string
  trigger: string
  score: number
}

export async function checkTriggers(prompt: string): Promise<{ matches: TriggerMatch[] }> {
  return request('/triggers/check', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

export interface UsageStats {
  period_days: number
  total_calls: number
  tool_breakdown: Record<string, number>
  skill_usage: Record<string, number>
  skill_last_used: Record<string, string>
  agent_breakdown: Record<string, number>
  never_used: string[]
  never_used_count: number
  total_skills: number
}

export async function getUsageStats(days: number): Promise<UsageStats> {
  return request(`/usage?days=${days}`)
}
