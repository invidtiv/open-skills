import type { Skill, SkillDetail, SkillFile, ValidationResult, Runbook, RunbookState } from './types'

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
