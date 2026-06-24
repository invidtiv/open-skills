import { useEffect, useState, createContext, useContext, useCallback } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export const useToast = () => useContext(ToastContext)

let nextId = 0
const MAX_TOASTS = 5

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = nextId++
    setToasts(prev => {
      const next = [...prev, { id, message, type }]
      return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next
    })
  }, [])

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(x => x.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onDone={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onDone }: { toast: Toast; onDone: () => void }) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 4000)
    const remove = setTimeout(onDone, 4300)
    return () => { clearTimeout(timer); clearTimeout(remove) }
  }, [onDone])

  const colors = {
    success: 'border-green bg-green/10 text-green',
    error: 'border-red bg-red/10 text-red',
    info: 'border-accent bg-accent/10 text-accent',
  }

  return (
    <div
      className={`flex items-start gap-2 px-4 py-3 rounded-lg border text-sm transition-opacity duration-300 ${colors[toast.type]} ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={onDone}
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity text-xs font-bold leading-none mt-0.5"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  )
}
