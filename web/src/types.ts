export interface Skill {
  name: string
  scope: string
  path: string
  description: string
  triggers: string[]
  boundaries: string[]
  required_tools: string[]
  output_format: string
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
