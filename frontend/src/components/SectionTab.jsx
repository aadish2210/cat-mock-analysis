import { Crosshair, Gauge, Rows3, TimerReset } from 'lucide-react'

import { useApi } from '../api'
import { formatNumber } from '../utils'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

const SECTION_COPY = {
  varc: { eyebrow: 'VARC strategy matrix', title: 'Read, select, eliminate', description: 'Banker conversion, passage pacing, and low-consensus exits across every attempt.' },
  dilr: { eyebrow: 'DILR strategy matrix', title: 'Set selection under pressure', description: 'Separate convertible sets from grinders and low-consensus traps.' },
  qa: { eyebrow: 'Quants strategy matrix', title: 'Convert the arithmetic core', description: 'Topic-level accuracy and pacing against empirical difficulty.' },
}

export default function SectionTab({ section, refreshKey, onImport }) {
  const { data, error, loading } = useApi(`/api/sections/${section}`, refreshKey)
  const copy = SECTION_COPY[section]
  if (loading) return <LoadingView label={`Building ${section.toUpperCase()} matrix`} />
  if (error) return <ErrorView message={error} />
  if (!data?.question_count) return <><SectionHeading {...copy} /><EmptyState title={`No ${section.toUpperCase()} questions found`} message="Import an IMS mock containing this section to populate the strategy matrix." onImport={onImport} /></>

  const matrixItems = [
    { key: 'bankers', label: 'Bankers / Type A', note: 'High empirical convertibility', tone: 'green' },
    { key: 'grinders', label: 'Grinders / Type B', note: 'Selective evaluation zone', tone: 'amber' },
    { key: 'traps', label: 'Traps / Type C', note: 'Low-consensus exit zone', tone: 'coral' },
  ]

  return (
    <div className="view-stack">
      <SectionHeading {...copy} />
      <MetricStrip metrics={[
        { label: 'Questions mapped', value: data.question_count },
        { label: 'Cumulative score', value: formatNumber(data.score), tone: data.score >= 0 ? 'tone-green' : 'tone-coral' },
        { label: 'Attempt accuracy', value: formatNumber(data.accuracy, '%') },
        { label: 'Time sinks', value: data.pacing.time_sink_count, tone: 'tone-coral', detail: `${data.pacing.average_seconds}s average pace` },
      ]} />

      <section className="data-section">
        <div className="data-section-title"><div><Crosshair size={19} /><h2>Difficulty matrix</h2></div><span>Empirical p-value classification</span></div>
        <div className="matrix-grid">{matrixItems.map((item) => { const stats = data.matrix[item.key]; return <article className={`matrix-panel matrix-${item.tone}`} key={item.key}><header><span>{item.label}</span><strong>{stats.count}</strong></header><p>{item.note}</p><div><span><small>Attempted</small><strong>{stats.attempted}/{stats.count}</strong></span><span><small>Accuracy</small><strong>{stats.accuracy}%</strong></span></div></article> })}</div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><Rows3 size={19} /><h2>Topic control board</h2></div><span>Candidate versus topper pace</span></div>
        <div className="table-wrap"><table><thead><tr><th>Topic</th><th>Volume</th><th>Attempted</th><th>Accuracy</th><th>Your pace</th><th>Topper pace</th><th>Gap</th></tr></thead><tbody>{data.topics.map((topic) => { const gap = topic.average_time_seconds - topic.topper_time_seconds; return <tr key={topic.topic}><td><strong>{topic.topic}</strong></td><td className="mono">{topic.questions}</td><td className="mono">{topic.attempted}</td><td className="mono">{topic.accuracy}%</td><td className="mono">{topic.average_time_seconds}s</td><td className="mono">{topic.topper_time_seconds || '-'}{topic.topper_time_seconds ? 's' : ''}</td><td className={`mono ${gap > 45 ? 'tone-coral' : gap > 0 ? 'tone-amber' : 'tone-green'}`}>{topic.topper_time_seconds ? `${gap > 0 ? '+' : ''}${Math.round(gap)}s` : '-'}</td></tr> })}</tbody></table></div>
      </section>

      <div className="pacing-band"><Gauge size={19} /><div><span>Average candidate pace</span><strong>{data.pacing.average_seconds}s</strong></div><TimerReset size={19} /><div><span>Non-scoring attempts over 3 minutes</span><strong>{data.pacing.time_sink_count}</strong></div></div>
    </div>
  )
}