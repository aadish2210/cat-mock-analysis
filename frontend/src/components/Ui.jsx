import { AlertTriangle, FileInput, LoaderCircle } from 'lucide-react'

export function LoadingView({ label = 'Loading analysis' }) {
  return <div className="state-view" role="status"><LoaderCircle className="spin" size={22} aria-hidden="true" /><span>{label}</span></div>
}

export function ErrorView({ message }) {
  return <div className="state-view state-error" role="alert"><AlertTriangle size={20} aria-hidden="true" /><span>{message}</span></div>
}

export function EmptyState({ title, message, onImport }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><FileInput size={24} aria-hidden="true" /></div>
      <p className="eyebrow">Awaiting source data</p>
      <h2>{title}</h2>
      <p>{message}</p>
      {onImport && <button className="button button-primary" type="button" onClick={onImport}><FileInput size={17} aria-hidden="true" /> Import IMS links</button>}
    </div>
  )
}

export function SectionHeading({ eyebrow, title, description, action }) {
  return (
    <header className="section-heading">
      <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p className="section-description">{description}</p>}</div>
      {action}
    </header>
  )
}

export function MetricStrip({ metrics }) {
  return (
    <div className="metric-strip">
      {metrics.map((metric) => <div className="metric" key={metric.label}><span className={`metric-value ${metric.tone || ''}`}>{metric.value}</span><span className="metric-label">{metric.label}</span>{metric.detail && <span className="metric-detail">{metric.detail}</span>}</div>)}
    </div>
  )
}

export function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}