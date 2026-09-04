import { useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  Clock3,
  Crosshair,
  Gauge,
  ListChecks,
  ShieldCheck,
  Target,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { apiFetch, useApi } from '../api'
import { formatNumber } from '../utils'
import QuestionModal from './QuestionModal'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

const QUADRANT_COPY = {
  protect: ['Protect', 'Accurate and near benchmark pace'],
  accelerate: ['Accelerate', 'Accurate, but time is leaking'],
  rebuild: ['Rebuild', 'Accuracy is below the stable zone'],
  select_better: ['Select better', 'Low return on low-consensus attempts'],
  sharpen: ['Sharpen', 'Middle zone: improve conversion'],
  observe: ['Observe', 'Not enough attempted evidence yet'],
}

const ERROR_COPY = {
  omission: ['Bankers omitted', 'Direct Type A opportunities skipped'],
  selection: ['Selection errors', 'Wrong attempts on Type C questions'],
  conversion: ['Conversion errors', 'Wrong attempts on Type A/B questions'],
  pacing: ['Speed leaks', 'Correct answers above 2.5x topper time'],
}

function trendTone(value) {
  if (value > 2) return 'tone-green'
  if (value < -2) return 'tone-coral'
  return 'tone-amber'
}

export default function CoachCockpit({ refreshKey, onImport }) {
  const { data, error, loading } = useApi('/api/coach', refreshKey)
  const [topicSection, setTopicSection] = useState('all')
  const [openQuestion, setOpenQuestion] = useState(null)
  const [questionError, setQuestionError] = useState('')

  if (loading) return <LoadingView label="Building your coaching brief" />
  if (error) return <ErrorView message={error} />
  if (!data?.mock_count) {
    return <><SectionHeading eyebrow="Coach cockpit" title="Your evidence plan" description="A ranked weekly plan generated from selection, conversion, pacing, and consistency data." /><EmptyState title="No evidence yet" message="Import an IMS attempt to build your first coaching brief." onImport={onImport} /></>
  }

  async function openQueueQuestion(item) {
    setQuestionError('')
    try {
      setOpenQuestion(await apiFetch(`/api/mocks/${encodeURIComponent(item.mock_slug)}/questions/${encodeURIComponent(item.id)}`))
    } catch (requestError) {
      setQuestionError(requestError.message)
    }
  }

  const topics = data.topic_matrix.filter((topic) => topicSection === 'all' || topic.section === topicSection)
  const scorecard = data.scorecard
  const TrendIcon = scorecard.trend_delta >= 0 ? ArrowUpRight : ArrowDownRight

  return (
    <div className="view-stack coach-view">
      <SectionHeading
        eyebrow={`Coach cockpit / ${data.mock_count} mocks`}
        title="Turn volatility into a repeatable score"
        description="Every action below is ranked from your own attempts, topper telemetry, and observed mark leakage."
        action={<div className={`trend-chip ${trendTone(scorecard.trend_delta)}`}><TrendIcon size={17} /><span><strong>{scorecard.trend_delta > 0 ? '+' : ''}{scorecard.trend_delta}</strong> recent-vs-prior</span></div>}
      />

      <MetricStrip metrics={[
        { label: 'Decision discipline', value: formatNumber(scorecard.discipline_index, '/100'), tone: 'tone-green', detail: 'Transparent composite, not a percentile' },
        { label: 'Recent average', value: formatNumber(scorecard.recent_average), detail: `Overall ${scorecard.average_score}` },
        { label: 'Best / floor', value: `${formatNumber(scorecard.best_score)} / ${formatNumber(scorecard.floor_score)}`, tone: 'tone-amber', detail: `${scorecard.volatility} score volatility` },
        { label: 'Potential gap', value: `+${formatNumber(scorecard.average_potential_gap)}`, tone: 'tone-coral', detail: 'Average factual correction bridge' },
      ]} />

      <section className="coach-grid coach-grid-primary">
        <div className="data-section coach-priorities">
          <div className="data-section-title"><div><Target size={19} /><h2>Next three moves</h2></div><span>Ranked by observed impact</span></div>
          <div className="priority-list">
            {data.priorities.slice(0, 5).map((priority, index) => (
              <article className={`priority-row priority-${priority.kind}`} key={`${priority.kind}-${priority.section}-${priority.topic}`}>
                <span className="priority-rank">{String(index + 1).padStart(2, '0')}</span>
                <div><small>{priority.section.toUpperCase()} / {priority.kind.replace('_', ' ')}</small><strong>{priority.title}</strong><p>{priority.detail}</p></div>
                <em>{priority.metric}</em>
              </article>
            ))}
          </div>
        </div>

        <div className="data-section coach-chart-section">
          <div className="data-section-title"><div><Activity size={19} /><h2>Score runway</h2></div><span>Actual versus tactical potential</span></div>
          <div className="coach-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.trajectory} margin={{ top: 14, right: 8, left: -23, bottom: 2 }}>
                <defs><linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4cc9a6" stopOpacity={0.28} /><stop offset="100%" stopColor="#4cc9a6" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke="rgba(255,255,255,.05)" vertical={false} />
                <XAxis dataKey="title" tick={{ fill: '#647287', fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#647287', fontSize: 9 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#111a28', border: '1px solid rgba(255,255,255,.12)', borderRadius: 5, fontSize: 11 }} />
                <Area type="monotone" dataKey="potential" stroke="#f0b35a" fill="none" strokeWidth={1.6} strokeDasharray="5 4" />
                <Area type="monotone" dataKey="score" stroke="#4cc9a6" fill="url(#actualFill)" strokeWidth={2.2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><Crosshair size={19} /><h2>Section operating system</h2></div><span>History-backed score floor and protocol</span></div>
        <div className="section-command-grid">
          {data.sections.map((section) => {
            const protocol = data.protocol.find((item) => item.section === section.section)
            return (
              <article className="section-command" key={section.section}>
                <header><strong>{section.section.toUpperCase()}</strong><span className={trendTone(section.trend_delta)}>{section.trend_delta > 0 ? '+' : ''}{section.trend_delta}</span></header>
                <div className="section-score-range"><span><small>Average</small><strong>{section.average_score}</strong></span><span><small>Best</small><strong>{section.best_score}</strong></span><span><small>Floor</small><strong>{section.floor_score}</strong></span></div>
                <dl><div><dt>Target attempts</dt><dd>{protocol.attempt_floor}-{protocol.attempt_ceiling}</dd></div><div><dt>Accuracy floor</dt><dd>{protocol.accuracy_floor}%</dd></div><div><dt>First-pass cap</dt><dd>{Math.floor(protocol.first_pass_cap_seconds / 60)}:{String(protocol.first_pass_cap_seconds % 60).padStart(2, '0')}</dd></div><div><dt>Avg potential gap</dt><dd>+{section.potential_gap}</dd></div></dl>
              </article>
            )
          })}
        </div>
      </section>

      <section className="coach-grid">
        <div className="data-section">
          <div className="data-section-title"><div><BrainCircuit size={19} /><h2>Decision leak ledger</h2></div><span>Independent diagnostic lenses</span></div>
          <div className="error-lens-grid">
            {data.error_lenses.map((lens) => <article key={lens.kind}><span className={`lens-symbol lens-symbol-${lens.kind}`} /><div><small>{ERROR_COPY[lens.kind][0]}</small><strong>{lens.count}</strong><p>{ERROR_COPY[lens.kind][1]}</p></div><em>{lens.marks ? `+${lens.marks} marks` : `${lens.minutes} min`}</em></article>)}
          </div>
        </div>
        <div className="data-section">
          <div className="data-section-title"><div><Clock3 size={19} /><h2>Pace ROI</h2></div><span>Attempted questions only</span></div>
          <div className="pace-roi-list">
            {data.pace_bands.map((band) => <div key={band.band}><span>{band.band.replaceAll('_', ' ').replace('to', '-')}</span><div className="bar-track"><i style={{ width: `${Math.min(100, Math.max(3, band.accuracy))}%` }} /></div><strong>{band.accuracy}%</strong><em>{band.marks_per_10_minutes} marks / 10m</em></div>)}
          </div>
        </div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><Gauge size={19} /><h2>Topic decision matrix</h2></div><div className="matrix-filters">{['all', 'varc', 'dilr', 'qa'].map((section) => <button className={topicSection === section ? 'is-selected' : ''} type="button" key={section} onClick={() => setTopicSection(section)}>{section.toUpperCase()}</button>)}</div></div>
        <div className="table-wrap coach-topic-table"><table><thead><tr><th>Topic</th><th>Decision</th><th>Volume</th><th>Accuracy</th><th>Pace</th><th>Missed A</th><th>Wrong C</th><th>Excess</th></tr></thead><tbody>{topics.slice(0, 24).map((topic) => <tr key={`${topic.section}-${topic.topic}`}><td><strong>{topic.topic}</strong><small>{topic.section.toUpperCase()}</small></td><td><span className={`quadrant quadrant-${topic.quadrant}`}>{QUADRANT_COPY[topic.quadrant][0]}</span></td><td className="mono">{topic.attempted}/{topic.question_count}</td><td className="mono">{topic.accuracy}%</td><td className="mono">{topic.pace_ratio ? `${topic.pace_ratio}x` : '-'}</td><td className="mono">{topic.missed_bankers}</td><td className="mono">{topic.wrong_traps}</td><td className="mono">{topic.excess_minutes}m</td></tr>)}</tbody></table></div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><ListChecks size={19} /><h2>Adaptive drill queue</h2></div><span>Highest-value reviews first</span></div>
        {questionError && <p className="form-error">{questionError}</p>}
        <div className="coach-queue">
          {data.practice_queue.slice(0, 12).map((item, index) => <button type="button" onClick={() => openQueueQuestion(item)} key={`${item.mock_slug}-${item.id}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{item.topic}</strong><small>{item.mock_title} / {item.section_slug.toUpperCase()} / Q{item.number}</small></div><em>{item.reason}</em><ArrowRight size={16} /></button>)}
        </div>
      </section>

      <details className="methodology"><summary><ShieldCheck size={16} /> How this plan is calculated</summary><p>{data.methodology.discipline_index}</p><p>{data.methodology.topic_quadrants}</p><p>{data.methodology.protocol}</p></details>
      {openQuestion && <QuestionModal question={openQuestion} onClose={() => setOpenQuestion(null)} />}
    </div>
  )
}