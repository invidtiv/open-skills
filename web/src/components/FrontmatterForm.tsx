import { useState } from 'react'

interface Props {
  frontmatter: Record<string, unknown>
  onChange: (fm: Record<string, unknown>) => void
}

export default function FrontmatterForm({ frontmatter, onChange }: Props) {
  const update = (key: string, value: unknown) => {
    onChange({ ...frontmatter, [key]: value })
  }

  return (
    <div className="space-y-4">
      <Field label="Name">
        <input
          type="text"
          value={(frontmatter.name as string) || ''}
          onChange={e => update('name', e.target.value)}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
        />
      </Field>
      <Field label="Description">
        <textarea
          value={(frontmatter.description as string) || ''}
          onChange={e => update('description', e.target.value)}
          rows={2}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none resize-none"
        />
      </Field>
      <TagField
        label="Triggers"
        values={(frontmatter.triggers as string[]) || []}
        onChange={v => update('triggers', v)}
      />
      <TagField
        label="Boundaries"
        values={(frontmatter.boundaries as string[]) || []}
        onChange={v => update('boundaries', v)}
      />
      <TagField
        label="Required Tools"
        values={(frontmatter.required_tools as string[]) || []}
        onChange={v => update('required_tools', v)}
      />
      <Field label="Output Format">
        <input
          type="text"
          value={(frontmatter.output_format as string) || ''}
          onChange={e => update('output_format', e.target.value)}
          className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
        />
      </Field>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-text-dim mb-1">{label}</label>
      {children}
    </div>
  )
}

function TagField({ label, values, onChange }: { label: string; values: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState('')

  const add = () => {
    const v = input.trim()
    if (v && !values.includes(v)) {
      onChange([...values, v])
      setInput('')
    }
  }

  const remove = (idx: number) => {
    onChange(values.filter((_, i) => i !== idx))
  }

  return (
    <Field label={label}>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {values.map((v, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 text-xs bg-bg-code border border-border rounded px-2 py-1 text-text-dim"
          >
            {v}
            <button onClick={() => remove(i)} className="text-red hover:text-red/80 ml-0.5">&times;</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), add())}
          placeholder={`Add ${label.toLowerCase()}...`}
          className="flex-1 bg-bg-code border border-border rounded-lg px-3 py-1.5 text-sm text-text focus:border-accent focus:outline-none"
        />
        <button
          onClick={add}
          className="px-3 py-1.5 text-xs font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors"
        >
          Add
        </button>
      </div>
    </Field>
  )
}
