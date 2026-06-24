import { Component, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from './components/Toast'
import Layout from './components/Layout'
import SkillsPage from './pages/SkillsPage'
import SkillDetailPage from './pages/SkillDetailPage'
import RunbooksPage from './pages/RunbooksPage'
import ExtractPage from './pages/ExtractPage'
import AgentSetupPage from './pages/AgentSetupPage'
import RecommendPage from './pages/RecommendPage'
import UsagePage from './pages/UsagePage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: unknown) {
    console.error('Uncaught error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-screen items-center justify-center p-6">
          <div className="max-w-md w-full rounded-xl border border-red bg-bg-card p-6 text-center">
            <h1 className="text-lg font-bold text-text">Something went wrong</h1>
            <p className="mt-3 text-sm text-red break-words">{this.state.error.message}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 px-4 py-2 rounded-lg text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <ErrorBoundary>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<SkillsPage />} />
                <Route path="/skills/:name" element={<SkillDetailPage />} />
                <Route path="/recommend" element={<RecommendPage />} />
                <Route path="/runbooks" element={<RunbooksPage />} />
                <Route path="/usage" element={<UsagePage />} />
                <Route path="/extract" element={<ExtractPage />} />
                <Route path="/agents" element={<AgentSetupPage />} />
              </Route>
            </Routes>
          </ErrorBoundary>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
