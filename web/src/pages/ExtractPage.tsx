import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { extractSkill } from '../api'
import { useToast } from '../components/Toast'

export default function ExtractPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: extractSkill,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast(`Extracted skill '${data.name}'`, 'success')
      navigate(`/skills/${encodeURIComponent(data.name)}`)
    },
    onError: (err: Error) => toast(err.message, 'error'),
  })

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-1">Extract Skill</h2>
      <p className="text-sm text-text-dim mb-6">
        Extract a repeatable procedure from your last chat session using AI.
      </p>

      <div className="max-w-lg p-6 bg-bg-card border border-border rounded-xl">
        <p className="text-sm text-text-dim mb-4">
          This reads your most recent Claude Code or Superpowers session transcript and sends it to
          DeepSeek V4 Flash via OpenRouter to identify repeatable technical procedures.
          The extracted skill will be saved to <code className="text-xs bg-bg-code px-1.5 py-0.5 rounded text-accent">pending-review/</code> for your review.
        </p>

        <div className="p-3 bg-bg-code border border-border rounded-lg text-xs text-text-dim mb-4">
          <p>Requires: <code className="text-accent">OPENROUTER_API_KEY</code> in environment or .env file</p>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full px-4 py-3 text-sm font-medium bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
        >
          {mutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Extracting from last session...
            </span>
          ) : (
            'Extract from Last Session'
          )}
        </button>
      </div>
    </div>
  )
}
