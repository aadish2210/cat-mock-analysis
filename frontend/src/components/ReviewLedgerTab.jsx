import { useState } from 'react'
import { ArrowRight, CalendarClock, CheckCircle2, History, NotebookTabs, RotateCcw } from 'lucide-react'

import { apiFetch, useApi } from '../api'
import QuestionModal from './QuestionModal'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

const STATUS_COPY = {
  again: 'Due tomorrow',
  learning: 'Three-day loop',
  mastered: 'Fourteen-day check',
}

export default function ReviewLedgerTab({ refreshKey, onImport }) {
  const [localRefresh, setLocalRefresh] = useState(0)
  const [openQuestion, setOpenQuestion] = useState(null)
  const [error, setError] = useState('')
  const reviews = useApi('/api/reviews', `${refreshKey}:${localRefresh}`)
  const coach = useApi('/api/coach', refreshKey)

  if (reviews.loading || coach.loading) return <LoadingView label="Building revision ledger" />
  if (reviews.error || coach.error) return <ErrorView message={reviews.error || coach.error} />
  if (!coach.data?.mock_count) return <><SectionHeading eyebrow="Review ledger" title="Remember what you repair" description="A lightweight spaced-review loop stored locally beside your mocks." /><EmptyState title="No questions to review" message="Import a mock to create the first adaptive queue." onImport={onImport} /></>

  async function openItem(item) {
    setError('')
    const mockSlug = item.mock_slug
    const questionId = item.question_id || item.id
    try {
      setOpenQuestion(await apiFetch(`/api/mocks/${encodeURIComponent(mockSlug)}/questions/${encodeURIComponent(questionId)}`))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  const due = reviews.data.reviews.filter((item) => item.is_due)
  const active = reviews.data.reviews.filter((item) => !item.is_due && item.status !== 'mastered')

  return (
    <div className="view-stack">
      <SectionHeading eyebrow="Review ledger" title="Remember what you repair" description="Mark questions while reviewing; the portal brings them back on a fixed 1, 3, or 14-day interval." />
      <MetricStrip metrics={[
        { label: 'Questions reviewed', value: reviews.data.count },
        { label: 'Due now', value: reviews.data.due_count, tone: reviews.data.due_count ? 'tone-coral' : 'tone-green' },
        { label: 'Learning', value: reviews.data.counts.learning, tone: 'tone-amber' },
        { label: 'Mastered', value: reviews.data.counts.mastered, tone: 'tone-green' },
      ]} />
      {error && <ErrorView message={error} />}

      <section className="data-section">
        <div className="data-section-title"><div><CalendarClock size={19} /><h2>Due queue</h2></div><span>{due.length} ready now</span></div>
        {due.length ? <div className="review-list">{due.map((item) => <button type="button" key={item.key} onClick={() => openItem(item)}><span className={`review-status review-${item.status}`}><RotateCcw size={15} /></span><div><strong>{item.question?.topic || 'Question unavailable'}</strong><small>{item.question?.mock_title} / {item.question?.section_slug?.toUpperCase()} / Q{item.question?.number}</small></div><em>{STATUS_COPY[item.status]}</em><ArrowRight size={16} /></button>)}</div> : <div className="inline-empty"><CheckCircle2 size={18} /> Nothing is due. Keep working the adaptive queue.</div>}
      </section>

      {active.length > 0 && <section className="data-section"><div className="data-section-title"><div><History size={19} /><h2>In learning</h2></div><span>Scheduled ahead</span></div><div className="review-list">{active.map((item) => <button type="button" key={item.key} onClick={() => openItem(item)}><span className={`review-status review-${item.status}`}><History size={15} /></span><div><strong>{item.question?.topic || 'Question unavailable'}</strong><small>{item.question?.mock_title} / next {new Date(item.next_review_at).toLocaleDateString()}</small></div><em>{item.review_count} reviews</em><ArrowRight size={16} /></button>)}</div></section>}

      <section className="data-section">
        <div className="data-section-title"><div><NotebookTabs size={19} /><h2>Recommended additions</h2></div><span>From the coach priority model</span></div>
        <div className="coach-queue">{coach.data.practice_queue.slice(0, 15).map((item, index) => <button type="button" onClick={() => openItem(item)} key={`${item.mock_slug}-${item.id}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{item.topic}</strong><small>{item.mock_title} / {item.section_slug.toUpperCase()} / Q{item.number}</small></div><em>{item.reason}</em><ArrowRight size={16} /></button>)}</div>
      </section>
      {openQuestion && <QuestionModal question={openQuestion} onClose={() => setOpenQuestion(null)} onReviewSaved={() => setLocalRefresh((value) => value + 1)} />}
    </div>
  )
}