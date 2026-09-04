import { BrainCircuit, Gauge, ShieldAlert, Sparkles, TimerReset } from 'lucide-react'

import { useApi } from '../api'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

function FindingRow({ item, kind }) {
  const trailing = kind === 'speed'
    ? `${item.speed_multiple}x topper time`
    : `${Math.round((item.topper_p_value || 0) * 100)}% topper accuracy`
  return (
    <div className="finding-row">
      <span className="finding-index">Q{item.number}</span>
      <div><strong>{item.topic || 'Unclassified'}</strong><small>{item.mock_title} / {item.section_slug?.toUpperCase()}</small></div>
      <span className="finding-value">{trailing}</span>
    </div>
  )
}

export default function TopperDivergenceTab({ refreshKey, onImport }) {
  const { data, error, loading } = useApi('/api/toppers/divergence', refreshKey)
  if (loading) return <LoadingView label="Comparing topper telemetry" />
  if (error) return <ErrorView message={error} />
  const totalFindings = (data?.topper_traps?.length || 0) + (data?.speed_gaps?.length || 0) + (data?.consensus_freebies_missed?.length || 0)
  if (!data || (!totalFindings && !data.topic_excess_minutes?.length)) return <><SectionHeading eyebrow="Topper divergence" title="Decisions versus the 99th percentile" description="Three empirical lenses separate selection errors from execution gaps." /><EmptyState title="No divergence telemetry yet" message="Import an IMS mock with topper statistics to unlock this comparison." onImport={onImport} /></>

  const lenses = [
    { key: 'topper_traps', title: 'Topper traps', subtitle: 'Low-consensus attempts that cost marks', icon: ShieldAlert, tone: 'coral', kind: 'trap' },
    { key: 'speed_gaps', title: 'Speed gaps', subtitle: 'Correct, but over 2.5x topper time', icon: TimerReset, tone: 'amber', kind: 'speed' },
    { key: 'consensus_freebies_missed', title: 'Consensus freebies', subtitle: 'Over 80% topper accuracy, missed', icon: Sparkles, tone: 'green', kind: 'freebie' },
  ]

  return (
    <div className="view-stack">
      <SectionHeading eyebrow="Topper divergence" title="Decisions versus the 99th percentile" description="Three empirical lenses separate selection errors from execution gaps." />
      <MetricStrip metrics={[
        { label: 'Topper traps', value: data.topper_traps.length, tone: 'tone-coral' },
        { label: 'Speed gaps', value: data.speed_gaps.length, tone: 'tone-amber' },
        { label: 'Freebies missed', value: data.consensus_freebies_missed.length, tone: 'tone-green' },
        { label: 'Topics over pace', value: data.topic_excess_minutes.length },
      ]} />

      <div className="lens-grid">
        {lenses.map(({ key, title, subtitle, icon: Icon, tone, kind }) => (
          <section className={`lens-panel lens-${tone}`} key={key}>
            <header><Icon size={19} /><div><h2>{title}</h2><p>{subtitle}</p></div><strong>{data[key].length}</strong></header>
            <div className="finding-list">{data[key].length ? data[key].map((item, index) => <FindingRow item={item} kind={kind} key={`${item.mock_slug}-${item.section_slug}-${item.id}-${index}`} />) : <div className="lens-empty">No findings</div>}</div>
          </section>
        ))}
      </div>

      <section className="data-section">
        <div className="data-section-title"><div><Gauge size={19} /><h2>Topic excess-minute leaderboard</h2></div><span>Candidate time minus topper time</span></div>
        <div className="leaderboard">{data.topic_excess_minutes.map((topic, index) => <div className="leader-row" key={topic.topic}><span>{String(index + 1).padStart(2, '0')}</span><strong>{topic.topic}</strong><div className="bar-track"><i style={{ width: `${Math.min(100, topic.excess_minutes / Math.max(data.topic_excess_minutes[0].excess_minutes, 1) * 100)}%` }} /></div><em>{topic.excess_minutes} min</em><small>{topic.questions} Qs</small></div>)}</div>
      </section>
      <div className="method-note"><BrainCircuit size={17} /><span>Only IMS-recorded candidate and topper telemetry is included.</span></div>
    </div>
  )
}