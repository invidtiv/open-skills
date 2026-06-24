import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getUsageStats } from '../api'
import type { UsageStats } from '../api'

const DAY_OPTIONS = [30, 90, 365]

export default function UsagePage() {
  const [days, setDays] = useState(90)
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['usage', days],
    queryFn: () => getUsageStats(days),
  })

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Usage Analytics</h2>
          <p className="text-sm text-text-dim mt-1">Skill and tool usage over the last {days} days</p>
        </div>
        <div className="flex gap-1.5">
          {DAY_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
                days === d
                  ? 'bg-accent/10 border-accent/30 text-accent'
                  : 'bg-bg-card border-border text-text-dim hover:text-text hover:border-accent'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="text-center py-16 text-text-dim animate-pulse">Loading usage...</div>}

      {isError && (
        <div className="p-4 bg-red/10 border border-red/30 rounded-xl text-sm text-red">
          {(error as Error).message}
        </div>
      )}

      {data && <UsageDashboard stats={data} />}
    </div>
  )
}

function UsageDashboard({ stats }: { stats: UsageStats }) {
  const topAgent = Object.entries(stats.agent_breakdown).sort((a, b) => b[1] - a[1])[0]
  const skillsUsedCount = Object.keys(stats.skill_usage).length

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total calls" value={stats.total_calls.toLocaleString()} />
        <StatCard label="Skills used" value={`${skillsUsedCount} / ${stats.total_skills}`} />
        <StatCard label="Never used" value={stats.never_used_count} accent="yellow" />
        <StatCard label="Top agent" value={topAgent ? topAgent[0] : '—'} sub={topAgent ? `${topAgent[1]} calls` : undefined} />
      </div>

      <BarSection title="Top Skills" data={stats.skill_usage} limit={10} linkSkills />
      <BarSection title="Tool Breakdown" data={stats.tool_breakdown} limit={10} />

      {Object.keys(stats.agent_breakdown).length > 0 && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Agent Activity</h3>
          <div className="bg-bg-card border border-border rounded-xl divide-y divide-border">
            {Object.entries(stats.agent_breakdown).sort((a, b) => b[1] - a[1]).map(([agent, count]) => (
              <div key={agent} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span className="font-mono text-text">{agent}</span>
                <span className="text-text-dim">{count.toLocaleString()} calls</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <NeverUsed skills={stats.never_used} count={stats.never_used_count} />
    </div>
  )
}

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: 'yellow' }) {
  return (
    <div className="p-5 bg-bg-card border border-border rounded-xl">
      <div className="text-xs text-text-dim mb-1">{label}</div>
      <div className={`text-2xl font-bold truncate ${accent === 'yellow' ? 'text-yellow' : 'text-text'}`}>{value}</div>
      {sub && <div className="text-xs text-text-dim mt-1">{sub}</div>}
    </div>
  )
}

function BarSection({ title, data, limit, linkSkills }: { title: string; data: Record<string, number>; limit: number; linkSkills?: boolean }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, limit)
  const max = entries.length > 0 ? entries[0][1] : 0

  return (
    <section>
      <h3 className="text-lg font-semibold mb-3">{title}</h3>
      {entries.length === 0 ? (
        <div className="p-5 bg-bg-card border border-border rounded-xl text-sm text-text-dim text-center">No data yet.</div>
      ) : (
        <div className="p-5 bg-bg-card border border-border rounded-xl space-y-2.5">
          {entries.map(([name, count]) => (
            <div key={name} className="flex items-center gap-3">
              <div className="w-40 shrink-0 text-sm truncate">
                {linkSkills ? (
                  <Link to={`/skills/${encodeURIComponent(name)}`} className="font-mono text-accent hover:underline">{name}</Link>
                ) : (
                  <span className="font-mono text-text">{name}</span>
                )}
              </div>
              <div className="flex-1 h-5 bg-bg-code rounded overflow-hidden">
                <div
                  className="h-full bg-accent/60 rounded"
                  style={{ width: `${max > 0 ? (count / max) * 100 : 0}%` }}
                />
              </div>
              <span className="w-12 shrink-0 text-right text-sm font-mono text-text-dim">{count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function NeverUsed({ skills, count }: { skills: string[]; count: number }) {
  const [open, setOpen] = useState(false)

  return (
    <section>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-lg font-semibold mb-3 hover:text-accent transition-colors"
      >
        <span>{open ? '▾' : '▸'}</span>
        Never Used Skills
        <span className="px-2 py-0.5 text-xs rounded-md bg-yellow/10 border border-yellow/30 text-yellow font-normal">{count}</span>
      </button>
      {open && (
        skills.length === 0 ? (
          <div className="p-5 bg-bg-card border border-border rounded-xl text-sm text-text-dim text-center">Every skill has been used.</div>
        ) : (
          <div className="p-5 bg-bg-card border border-border rounded-xl flex flex-wrap gap-2">
            {skills.map(name => (
              <Link
                key={name}
                to={`/skills/${encodeURIComponent(name)}`}
                className="px-2.5 py-1 text-xs rounded-md bg-bg-code border border-border font-mono text-text-dim hover:text-accent hover:border-accent transition-colors"
              >
                {name}
              </Link>
            ))}
          </div>
        )
      )}
    </section>
  )
}
