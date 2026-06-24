import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listAgents, connectAgent, disconnectAgent, customConnectAgent } from '../api'
import { useToast } from '../components/Toast'
import type { Agent, AgentActionResponse } from '../types'

export default function AgentSetupPage() {
  const { data, isLoading } = useQuery({ queryKey: ['agents'], queryFn: listAgents })
  const agents = data?.agents || []

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Agent Setup</h2>
        <p className="text-sm text-text-dim mt-1">
          Register the Open Skills MCP server into your agent's config. No secrets or tokens required — just config file paths.
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-text-dim animate-pulse">Detecting agents...</div>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 text-text-dim">
          <p className="text-lg">No agents detected.</p>
          <p className="text-sm mt-2">Use the manual target form below to register into any config path.</p>
        </div>
      ) : (
        <div className="space-y-3 mb-8">
          {agents.map(a => (
            <AgentCard key={a.id} agent={a} />
          ))}
        </div>
      )}

      <ManualTargetForm />
    </div>
  )
}

function AgentCard({ agent }: { agent: Agent }) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [showDiff, setShowDiff] = useState(false)
  const [diff, setDiff] = useState('')
  const [isDryRun, setIsDryRun] = useState(false)

  const connectMut = useMutation({
    mutationFn: (dryRun: boolean) => connectAgent(agent.id, 'all', dryRun),
    onSuccess: (data: AgentActionResponse) => {
      if (isDryRun) {
        setDiff(data.diff || '')
        setShowDiff(true)
      } else {
        queryClient.invalidateQueries({ queryKey: ['agents'] })
        toast(`${agent.label}: ${data.action}`, 'success')
      }
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const disconnectMut = useMutation({
    mutationFn: () => disconnectAgent(agent.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast(`${agent.label}: uninstalled`, 'success')
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const handleConnect = () => {
    setIsDryRun(true)
    connectMut.mutate(true)
  }
  const handleApply = () => {
    setShowDiff(false)
    setIsDryRun(false)
    connectMut.mutate(false)
  }

  const handleReconnect = () => {
    setIsDryRun(false)
    connectMut.mutate(false)
  }

  return (
    <div className="p-5 bg-bg-card border border-border rounded-xl">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-text">{agent.label}</h3>
            {agent.detected ? (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-green/15 text-green border border-green/30">
                Detected
              </span>
            ) : (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-bg-code text-text-dim border border-border">
                Not Detected
              </span>
            )}
            {agent.installed && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30">
                Open Skills Installed
              </span>
            )}
          </div>
          <p className="text-xs text-text-dim font-mono truncate">{agent.configPath}</p>
        </div>
        <div className="flex gap-2 shrink-0">
          {agent.installed ? (
            <>
              <button
                onClick={handleReconnect}
                disabled={connectMut.isPending}
                className="px-3 py-1.5 text-sm font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors disabled:opacity-50"
              >
                {connectMut.isPending ? '...' : 'Reconnect'}
              </button>
              <button
                onClick={() => disconnectMut.mutate()}
                disabled={disconnectMut.isPending}
                className="px-3 py-1.5 text-sm font-medium bg-red/10 border border-red/30 rounded-lg text-red hover:bg-red/20 transition-colors disabled:opacity-50"
              >
                {disconnectMut.isPending ? '...' : 'Disconnect'}
              </button>
            </>
          ) : (
            <button
              onClick={handleConnect}
              disabled={connectMut.isPending || !agent.detected}
              className="px-3 py-1.5 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
            >
              {connectMut.isPending ? '...' : 'Connect'}
            </button>
          )}
        </div>
      </div>

      {showDiff && diff && (
        <div className="mt-4">
          <pre className="text-xs bg-bg-code border border-border rounded-lg p-3 overflow-x-auto text-text-dim max-h-48 overflow-y-auto">{diff}</pre>
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleApply}
              className="px-3 py-1.5 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20"
            >
              Apply
            </button>
            <button
              onClick={() => setShowDiff(false)}
              className="px-3 py-1.5 text-sm text-text-dim hover:text-text"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ManualTargetForm() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [configPath, setConfigPath] = useState('')
  const [format, setFormat] = useState('mcp-json')
  const [scope, setScope] = useState('all')
  const [showDiff, setShowDiff] = useState(false)
  const [diff, setDiff] = useState('')

  const dryRunMut = useMutation({
    mutationFn: () => customConnectAgent(configPath, format, scope, true),
    onSuccess: (data: AgentActionResponse) => {
      setDiff(data.diff || '')
      setShowDiff(true)
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  const applyMut = useMutation({
    mutationFn: () => customConnectAgent(configPath, format, scope, false),
    onSuccess: (data: AgentActionResponse) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast(`Custom target: ${data.action} at ${data.path}`, 'success')
      setShowDiff(false)
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <div className="p-5 bg-bg-card border border-border rounded-xl">
      <h3 className="font-semibold text-text mb-1">Manual Target</h3>
      <p className="text-xs text-text-dim mb-4">
        Register into any agent's config file by path. Useful for unsupported or custom harnesses.
      </p>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-text-dim mb-1">Config File Path</label>
          <input
            type="text"
            value={configPath}
            onChange={e => setConfigPath(e.target.value)}
            placeholder="/path/to/mcp.json"
            className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          />
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-text-dim mb-1">Format</label>
            <select
              value={format}
              onChange={e => setFormat(e.target.value)}
              className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
            >
              <option value="mcp-json">mcp-json</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-text-dim mb-1">Scope</label>
            <select
              value={scope}
              onChange={e => setScope(e.target.value)}
              className="w-full bg-bg-code border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
            >
              <option value="all">All</option>
              <option value="local">Local</option>
              <option value="global">Global</option>
            </select>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => dryRunMut.mutate()}
            disabled={!configPath.trim() || dryRunMut.isPending}
            className="px-4 py-2 text-sm font-medium bg-bg-code border border-border rounded-lg text-text-dim hover:text-text hover:border-accent transition-colors disabled:opacity-50"
          >
            {dryRunMut.isPending ? 'Testing...' : 'Test Path (Dry Run)'}
          </button>
        </div>

        {showDiff && diff && (
          <div>
            <pre className="text-xs bg-bg-code border border-border rounded-lg p-3 overflow-x-auto text-text-dim max-h-48 overflow-y-auto">{diff}</pre>
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => applyMut.mutate()}
                disabled={applyMut.isPending}
                className="px-4 py-2 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 disabled:opacity-50"
              >
                {applyMut.isPending ? 'Applying...' : 'Apply'}
              </button>
              <button
                onClick={() => setShowDiff(false)}
                className="px-4 py-2 text-sm text-text-dim hover:text-text"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
