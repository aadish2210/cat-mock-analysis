import { BarChart3, Binary, BookOpenCheck, BrainCircuit, ChartNoAxesCombined, Database, FileSearch, Gauge, Layers3, NotebookTabs, Plus, Radar, Sigma, TextSearch } from 'lucide-react'

const NAV_ITEMS = [
  { id: 'coach', label: 'Coach cockpit', meta: 'Priority command', icon: Radar },
  { id: 'audit', label: 'Mock-wise audit', meta: '100+ roadmap', icon: FileSearch },
  { id: 'divergence', label: 'Topper divergence', meta: 'Decision gaps', icon: BrainCircuit },
  { id: 'simulator', label: 'What-if simulator', meta: 'Rule engine', icon: Binary },
  { id: 'varc', label: 'VARC matrix', meta: 'Section strategy', icon: TextSearch },
  { id: 'dilr', label: 'DILR matrix', meta: 'Set selection', icon: Layers3 },
  { id: 'qa', label: 'Quants matrix', meta: 'Topic control', icon: Sigma },
  { id: 'drill', label: 'Quants re-solve', meta: 'Type A lab', icon: BookOpenCheck },
  { id: 'review', label: 'Review ledger', meta: 'Spaced revision', icon: NotebookTabs },
  { id: 'trends', label: 'Macro trends', meta: 'Trajectory', icon: ChartNoAxesCombined },
  { id: 'questions', label: 'Question bank', meta: 'Full archive', icon: BarChart3 },
]

export default function Navbar({ active, mockCount, onSelect, onImport, storageMode }) {
  return (
    <aside className="side-rail">
      <div className="brand-block"><div className="brand-mark"><Gauge size={21} strokeWidth={2.2} aria-hidden="true" /></div><div><strong>CAT / DIAGNOSTIC</strong><span>Strategic intelligence</span></div></div>
      <nav className="primary-nav" aria-label="Portal sections">
        {NAV_ITEMS.map(({ id, label, meta, icon: Icon }) => (
          <button className={`nav-item ${active === id ? 'is-active' : ''}`} type="button" key={id} aria-current={active === id ? 'page' : undefined} onClick={() => onSelect(id)}>
            <Icon size={18} aria-hidden="true" /><span><strong>{label}</strong><small>{meta}</small></span>
          </button>
        ))}
      </nav>
      <div className="rail-footer">
        <div className="storage-status"><Database size={16} aria-hidden="true" /><span><strong>{mockCount} mocks</strong><small>{storageMode === 'supabase' ? 'Supabase cloud' : 'Local JSON file'}</small></span></div>
        <button className="button button-primary import-button" type="button" onClick={onImport}><Plus size={17} aria-hidden="true" /> Import mock</button>
      </div>
    </aside>
  )
}