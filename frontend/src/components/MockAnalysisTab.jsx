import { useState } from 'react'
import { ArrowRight, ClockAlert, Grid3X3, ListChecks, Route } from 'lucide-react'

import { useApi } from '../api'
import { formatNumber } from '../utils'
import { Badge, EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'
import QuestionModal from './QuestionModal'

export default function MockAnalysisTab({ refreshKey, onImport }) {
  const [selectedSlug, setSelectedSlug] = useState('')
  const [openQuestion, setOpenQuestion] = useState(null)
  const mocksState = useApi('/api/mocks', refreshKey)
  const currentSlug = selectedSlug || mocksState.data?.[0]?.slug || ''
  const auditState = useApi(currentSlug ? `/api/mocks/${currentSlug}` : null, refreshKey)

  if (mocksState.loading) return <LoadingView label="Loading mock index" />
  if (mocksState.error) return <ErrorView message={mocksState.error} />
  if (!mocksState.data?.length) return <><SectionHeading eyebrow="Mock-wise audit" title="The 100+ roadmap" description="Repair selection and pacing errors using marks you demonstrably left on the table." /><EmptyState title="Import your first mock" message="The audit needs one completed IMS attempt before it can calculate a realistic potential score." onImport={onImport} /></>
  if (auditState.loading || !auditState.data) return <LoadingView label="Auditing decisions" />
  if (auditState.error) return <ErrorView message={auditState.error} />

  const audit = auditState.data
  const potentialGain = audit.potential.potential - audit.potential.actual

  return (
    <div className="view-stack">
      <SectionHeading
        eyebrow="Mock-wise audit / 100+ roadmap"
        title={audit.mock.title}
        description="Actual performance separated from avoidable penalties, missed bankers, and pacing trade-offs."
        action={<label className="compact-select"><span className="sr-only">Select mock</span><select value={currentSlug} onChange={(event) => setSelectedSlug(event.target.value)}>{mocksState.data.map((mock) => <option value={mock.slug} key={mock.slug}>{mock.title}</option>)}</select></label>}
      />

      <MetricStrip metrics={[
        { label: 'Actual score', value: formatNumber(audit.potential.actual) },
        { label: 'Realistic potential', value: formatNumber(audit.potential.potential), tone: 'tone-green', detail: `+${potentialGain} recoverable` },
        { label: 'Trap penalties', value: formatNumber(audit.potential.traps_avoided), tone: 'tone-coral', detail: 'Marks saved by walking away' },
        { label: 'Type A recovery', value: formatNumber(audit.potential.skipped_type_a_gain + audit.potential.incorrect_type_a_gain), tone: 'tone-amber', detail: `${audit.potential.skipped_type_a_count + audit.potential.incorrect_type_a_count} decisions` },
      ]} />

      <section className="data-section">
        <div className="data-section-title"><div><Route size={19} /><h2>Potential score bridge</h2></div><span>Factual mark movement</span></div>
        <div className="score-bridge">
          <div><small>ACTUAL</small><strong>{audit.potential.actual}</strong></div><ArrowRight size={18} />
          <div><small>TRAPS AVOIDED</small><strong className="tone-coral">+{audit.potential.traps_avoided}</strong></div><ArrowRight size={18} />
          <div><small>SKIPPED A</small><strong className="tone-amber">+{audit.potential.skipped_type_a_gain}</strong></div><ArrowRight size={18} />
          <div><small>INCORRECT A</small><strong className="tone-amber">+{audit.potential.incorrect_type_a_gain}</strong></div><ArrowRight size={18} />
          <div className="bridge-total"><small>POTENTIAL</small><strong>{audit.potential.potential}</strong></div>
        </div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><ListChecks size={19} /><h2>Section audit</h2></div><span>Score / attempts / accuracy</span></div>
        <div className="table-wrap"><table><thead><tr><th>Section</th><th>Score</th><th>Attempted</th><th>Accuracy</th><th>Time</th></tr></thead><tbody>{audit.sections.map((section) => <tr key={section.slug}><td><strong>{section.title}</strong></td><td className="mono">{section.score}</td><td className="mono">{section.attempted}/{section.question_count}</td><td className="mono">{section.accuracy}%</td><td className="mono">{section.time_minutes} min</td></tr>)}</tbody></table></div>
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><ClockAlert size={19} /><h2>Direct trade-off</h2></div><span>Time sinks versus starved bankers</span></div>
        {audit.trade_offs.length ? <div className="trade-list">{audit.trade_offs.map((trade) => <article className="trade-row" key={trade.section}><div className="trade-section"><Badge>{trade.section}</Badge><strong>{trade.section_title}</strong><small>{trade.recoverable_minutes} min above cap</small></div><div><span className="trade-label tone-coral">Time sinks</span>{trade.time_sinks.length ? trade.time_sinks.map((question) => <button className="question-link" type="button" onClick={() => setOpenQuestion(audit.questions.find((item) => item.id === question.id))} key={question.id}>Q{question.number} · {Math.round(question.time_taken / 60)}m · {question.topic}</button>) : <span className="muted-copy">None</span>}</div><ArrowRight className="trade-arrow" size={18} /><div><span className="trade-label tone-green">Starved Type A</span>{trade.starved_freebies.length ? trade.starved_freebies.map((question) => <button className="question-link" type="button" onClick={() => setOpenQuestion(audit.questions.find((item) => item.id === question.id))} key={question.id}>Q{question.number} · {question.topic}</button>) : <span className="muted-copy">None</span>}</div><div className="trade-marks"><strong>+{trade.available_marks}</strong><small>available marks</small></div></article>)}</div> : <div className="inline-empty">No time-sink or missed-banker trade-offs were found in this attempt.</div>}
      </section>

      <section className="data-section">
        <div className="data-section-title"><div><Grid3X3 size={19} /><h2>Question palette</h2></div><div className="palette-legend"><span><i className="legend-dot correct" /> Correct</span><span><i className="legend-dot wrong" /> Incorrect</span><span><i className="legend-dot skipped" /> Skipped</span></div></div>
        <div className="question-palette">{audit.questions.map((question) => <button className={`palette-cell ${!question.is_attempted ? 'skipped' : question.is_correct ? 'correct' : 'wrong'}`} type="button" key={`${question.section_slug}-${question.id}`} onClick={() => setOpenQuestion(question)} title={`${question.section_title} Q${question.number}: ${question.topic}`}><span>{question.number}</span><small>{question.section_slug}</small><i>{question.difficulty}</i></button>)}</div>
      </section>
      {openQuestion && <QuestionModal question={openQuestion} onClose={() => setOpenQuestion(null)} />}
    </div>
  )
}