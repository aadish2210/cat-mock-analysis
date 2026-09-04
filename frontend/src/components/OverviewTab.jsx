import { Activity, Clock3, Target } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { useApi } from '../api'
import { formatNumber } from '../utils'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

export default function OverviewTab({ refreshKey, onImport }) {
  const { data, error, loading } = useApi('/api/summary', refreshKey)
  if (loading) return <LoadingView label="Building macro trends" />
  if (error) return <ErrorView message={error} />
  if (!data?.mock_count) return <><SectionHeading eyebrow="Macro trends" title="Your attempt trajectory" description="Scores, section stability, and decision quality across the most recent 16 mocks." /><EmptyState title="No mocks imported yet" message="Import fresh IMS View Solutions links to build your first factual trend line." onImport={onImport} /></>

  return (
    <div className="view-stack">
      <SectionHeading eyebrow="Macro trends" title="Your attempt trajectory" description="Scores, section stability, and decision quality across the most recent 16 mocks." />
      <MetricStrip metrics={[{ label: 'Mocks audited', value: data.mock_count }, { label: 'Average score', value: formatNumber(data.average_score), tone: 'tone-green' }, { label: 'Attempt accuracy', value: formatNumber(data.average_accuracy, '%') }, { label: 'Time sinks', value: data.time_sinks.count, detail: `${data.time_sinks.minutes} min invested`, tone: 'tone-coral' }]} />
      <section className="data-section">
        <div className="data-section-title"><div><Activity size={19} aria-hidden="true" /><h2>Score versus realistic potential</h2></div><span>Last 16 attempts</span></div>
        <div className="chart-frame" aria-label="Score trajectory chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.trajectory} margin={{ top: 16, right: 18, left: -16, bottom: 6 }}><CartesianGrid stroke="rgba(255,255,255,0.055)" vertical={false} /><XAxis dataKey="title" tick={{ fill: '#738096', fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" /><YAxis tick={{ fill: '#738096', fontSize: 11 }} tickLine={false} axisLine={false} /><Tooltip contentStyle={{ background: '#111a28', border: '1px solid rgba(255,255,255,.12)', borderRadius: 6 }} /><Legend wrapperStyle={{ fontSize: 12, color: '#9aa8bb' }} /><Line name="Actual" type="monotone" dataKey="score" stroke="#4cc9a6" strokeWidth={2.4} dot={{ r: 3, fill: '#4cc9a6' }} activeDot={{ r: 5 }} /><Line name="Potential" type="monotone" dataKey="potential" stroke="#f0b35a" strokeWidth={2} strokeDasharray="6 5" dot={false} /></LineChart></ResponsiveContainer></div>
      </section>
      <section className="data-section">
        <div className="data-section-title"><div><Target size={19} aria-hidden="true" /><h2>Section stability</h2></div><span>All imported attempts</span></div>
        <div className="section-bars">{data.section_averages.map((section) => <div className="section-bar" key={section.section}><strong>{section.section.toUpperCase()}</strong><div className="bar-track"><span style={{ width: `${Math.min(section.accuracy, 100)}%` }} /></div><span>{section.average_score} avg</span><small><Clock3 size={13} aria-hidden="true" /> {section.average_time_seconds}s / question</small></div>)}</div>
      </section>
    </div>
  )
}