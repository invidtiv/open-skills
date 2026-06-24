import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { recommendSkills, checkTriggers } from '../api'
import type { RecommendResult } from '../types'
import type { TriggerMatch } from '../api'

export default function RecommendPage() {
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState('all')

  const recommend = useMutation<RecommendResult, Error, void>({
    mutationFn: () => recommendSkills(query, 5, scope),
  })

  const result = recommend.data

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Recommend Skills</h2>
        <p className="text-sm text-text-dim mt-1">Find the right skill for your task</p>
      </div>

      <form
        onSubmit={e => { e.preventDefault(); if (query.trim()) recommend.mutate() }}
        className="mb-6"
      >
        <textarea
          value={query}
          onChange={e => setQuery(e.target.value)}
          rows={3}
          placeholder="Describe what you want to do..."
          className="w-full bg-bg-code border border-border rounded-lg px-4 py-3 text-sm text-text placeholder:text-text-dim/50 focus:border-accent focus:outline-none resize-none mb-3"
        />
        <div className="flex items-center gap-2">
          <select
            value={scope}
            onChange={e => setScope(e.target.value)}
            className="bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          >
            <option value="all">All scopes</option>
            <option value="global">Global</option>
            <option value="local">Local</option>
          </select>
          <button
            type="submit"
            disabled={!query.trim() || recommend.isPending}
            className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50 transition-colors"
          >
            {recommend.isPending ? 'Searching...' : 'Find Skills'}
          </button>
        </div>
      </form>

      {recommend.isError && (
        <div className="mb-6 p-4 bg-red/10 border border-red/30 rounded-xl text-sm text-red">
          {recommend.error.message}
        </div>
      )}

      {result && (
        <div className="mb-10">
          <div className="flex items-center justify-between mb-3 text-xs text-text-dim">
            <span>{result.candidate_count} candidates scanned in {result.elapsed_ms}ms</span>
            <span>
              {result.llm_used
                ? `LLM ranked${result.model ? ` · ${result.model}` : ''}`
                : 'Keyword ranked (no LLM)'}
            </span>
          </div>

          {result.results.length === 0 ? (
            <div className="text-center py-12 text-text-dim">No matching skills found.</div>
          ) : (
            <div className="space-y-3">
              {result.results.map(item => (
                <div key={`${item.scope}-${item.name}`} className="p-5 bg-bg-card border border-border rounded-xl">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <Link
                      to={`/skills/${encodeURIComponent(item.name)}`}
                      className="font-mono text-sm font-semibold text-accent hover:underline"
                    >
                      {item.name}
                    </Link>
                    <span className="px-2 py-0.5 text-[11px] rounded-md bg-bg-code border border-border text-text-dim shrink-0">
                      {item.scope}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex-1 h-1.5 bg-bg-code rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${Math.max(0, Math.min(1, item.score)) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-text-dim w-10 text-right">{item.score.toFixed(2)}</span>
                  </div>

                  {item.reason && <p className="text-sm text-text-dim mb-3">{item.reason}</p>}

                  {item.triggers.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {item.triggers.map((t, i) => (
                        <span key={i} className="px-2 py-0.5 text-[11px] rounded-md bg-bg-code border border-border text-text-dim">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <TriggerChecker />
    </div>
  )
}

function TriggerChecker() {
  const [prompt, setPrompt] = useState('')

  const check = useMutation<{ matches: TriggerMatch[] }, Error, void>({
    mutationFn: () => checkTriggers(prompt),
  })

  const matches = check.data?.matches

  return (
    <div className="border-t border-border pt-8">
      <h3 className="text-lg font-semibold mb-1">Trigger Checker</h3>
      <p className="text-sm text-text-dim mb-4">Test which skills a prompt would auto-trigger.</p>

      <form
        onSubmit={e => { e.preventDefault(); if (prompt.trim()) check.mutate() }}
        className="flex items-center gap-2 mb-4"
      >
        <input
          type="text"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Paste a prompt to test trigger matching"
          className="flex-1 bg-bg-code border border-border rounded-lg px-4 py-2 text-sm text-text placeholder:text-text-dim/50 focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={!prompt.trim() || check.isPending}
          className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50 transition-colors shrink-0"
        >
          {check.isPending ? 'Checking...' : 'Check Triggers'}
        </button>
      </form>

      {check.isError && (
        <div className="p-4 bg-red/10 border border-red/30 rounded-xl text-sm text-red">
          {check.error.message}
        </div>
      )}

      {matches && (
        matches.length === 0 ? (
          <div className="text-center py-8 text-text-dim text-sm">No triggers matched this prompt.</div>
        ) : (
          <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-text-dim">
                  <th className="px-4 py-2 font-medium">Skill</th>
                  <th className="px-4 py-2 font-medium">Trigger</th>
                  <th className="px-4 py-2 font-medium text-right">Score</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((m, i) => (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td className="px-4 py-2">
                      <Link
                        to={`/skills/${encodeURIComponent(m.skill)}`}
                        className="font-mono text-accent hover:underline"
                      >
                        {m.skill}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-text-dim">{m.trigger}</td>
                    <td className="px-4 py-2 text-right font-mono text-text-dim">{m.score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  )
}
