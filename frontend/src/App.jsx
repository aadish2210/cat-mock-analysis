import { lazy, startTransition, Suspense, useState } from 'react'
import { Plus } from 'lucide-react'

import './App.css'
import { useApi } from './api'
import { useAuth } from './auth-context'
import AuthScreen from './components/AuthScreen'
import ImportModal from './components/ImportModal'
import Navbar from './components/Navbar'
import ProfileMenu from './components/ProfileMenu'
import { LoadingView } from './components/Ui'

const CoachCockpit = lazy(() => import('./components/CoachCockpit'))
const MockAnalysisTab = lazy(() => import('./components/MockAnalysisTab'))
const OverviewTab = lazy(() => import('./components/OverviewTab'))
const QuantsDrillTab = lazy(() => import('./components/QuantsDrillTab'))
const QuestionBankTab = lazy(() => import('./components/QuestionBankTab'))
const ReviewLedgerTab = lazy(() => import('./components/ReviewLedgerTab'))
const SectionTab = lazy(() => import('./components/SectionTab'))
const TopperDivergenceTab = lazy(() => import('./components/TopperDivergenceTab'))
const WhatIfSimulatorTab = lazy(() => import('./components/WhatIfSimulatorTab'))

function App() {
  const { config, error, loading, user } = useAuth()
  if (loading) return <div className="app-boot"><span className="status-dot" /><strong>Opening secure workspace</strong></div>
  if (error && !config) return <div className="app-boot app-boot-error"><strong>Configuration error</strong><span>{error}</span></div>
  if (config?.auth_enabled && !user) return <AuthScreen />
  return <PortalApp />
}

function PortalApp() {
  const { config } = useAuth()
  const [activeTab, setActiveTab] = useState('coach')
  const [importOpen, setImportOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const { data: summary } = useApi('/api/summary', refreshKey)

  function selectTab(tab) {
    startTransition(() => setActiveTab(tab))
  }

  function imported() {
    setRefreshKey((key) => key + 1)
    startTransition(() => setActiveTab('audit'))
  }

  let activeView
  if (activeTab === 'coach') activeView = <CoachCockpit refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'trends') activeView = <OverviewTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'audit') activeView = <MockAnalysisTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'divergence') activeView = <TopperDivergenceTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'simulator') activeView = <WhatIfSimulatorTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (['varc', 'dilr', 'qa'].includes(activeTab)) activeView = <SectionTab section={activeTab} refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'drill') activeView = <QuantsDrillTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'review') activeView = <ReviewLedgerTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else if (activeTab === 'questions') activeView = <QuestionBankTab refreshKey={refreshKey} onImport={() => setImportOpen(true)} />
  else activeView = <CoachCockpit refreshKey={refreshKey} onImport={() => setImportOpen(true)} />

  return (
    <div className="app-shell">
      <Navbar active={activeTab} mockCount={summary?.mock_count || 0} onSelect={selectTab} onImport={() => setImportOpen(true)} storageMode={config.mode} />
      <main className="main-stage">
        <header className="top-bar"><div className="system-state"><span className="status-dot" /> Analysis engine ready</div><div className="top-context">{config.mode === 'supabase' ? 'Cloud persistence' : 'JSON persistence'} <span>/</span> Private workspace</div><button className="button button-compact" type="button" onClick={() => setImportOpen(true)}><Plus size={16} aria-hidden="true" /> Add attempt</button><ProfileMenu /></header>
        <div className="content-frame" key={activeTab}>
          <Suspense fallback={<LoadingView label="Opening workspace" />}>{activeView}</Suspense>
        </div>
      </main>
      {importOpen && <ImportModal onClose={() => setImportOpen(false)} onImported={imported} />}
    </div>
  )
}

export default App
