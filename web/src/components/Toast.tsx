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

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = nextId++
    setToasts(prev => [...prev, { id, message, type }])
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onDone={() => setToasts(prev => prev.filter(x => x.id !== t.id))} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onDone }: { toast: Toast; onDone: () => void }) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 3000)
    const remove = setTimeout(onDone, 3300)
    return () => { clearTimeout(timer); clearTimeout(remove) }
  }, [onDone])

  const colors = {
    success: 'border-green bg-green/10 text-green',
    error: 'border-red bg-red/10 text-red',
    info: 'border-accent bg-accent/10 text-accent',
  }

  return (
    <div
      className={`px-4 py-3 rounded-lg border text-sm transition-opacity duration-300 ${colors[toast.type]} ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {toast.message}
    </div>
  )
}
