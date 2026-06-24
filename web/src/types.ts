export interface Skill {
  name: string
  scope: string
  path: string
  description: string
  triggers: string[]
  boundaries: string[]
  required_tools: string[]
  output_format: string
  disable_model_invocation: boolean
  user_invocable: boolean
}

export interface SkillDetail extends Skill {
  dir: string
  content: string
  frontmatter: Record<string, unknown>
  body: string
  files: string[]
}

export interface SkillFile {
  path: string
  size: number
}

export interface ValidationCheck {
  label: string
  passed: boolean
  detail: string
}

export interface ValidationResult {
  valid: boolean
  checks: ValidationCheck[]
  errors: string[]
  warnings: string[]
}

export interface Runbook {
  name: string
  scope: string
  path: string
  phase_count: number
}

export interface RunbookPhase {
  phase: string
  skill: string
  input: string
  output: string
  status: string
}

export interface RunbookState {
  active: boolean
  runbook?: string
  current_phase?: string | null
  phases?: RunbookPhase[]
  updated_at?: string
}

export interface Agent {
  id: string
  label: string
  detected: boolean
  installed: boolean
  configPath: string
  format: string
}

export interface AgentActionResponse {
  action: string
  path: string
  diff?: string
  error?: string
}

export interface RecommendResult {
  query: string
  llm_used: boolean
  model: string | null
  results: RecommendItem[]
  candidate_count: number
  elapsed_ms: number
}

export interface RecommendItem {
  name: string
  scope: string
  score: number
  reason: string
  triggers: string[]
}
