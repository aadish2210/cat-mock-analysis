import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import DOMPurify from 'dompurify'
import { BookOpenCheck, CalendarClock, CheckCircle2, Clock3, Lightbulb, LoaderCircle, RotateCcw, Save, X, XCircle } from 'lucide-react'

import { apiFetch } from '../api'
import { Badge } from './Ui'

function SafeHtml({ html, className = '' }) {
  return <div className={`rich-content ${className}`} dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(String(html || '')) }} />
}

function answerLabel(value) {
  if (value === null || value === undefined || value === '') return 'No answer'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function QuestionModal({ question, onClose, revealSolution = true, onReviewSaved }) {
  const [review, setReview] = useState(null)
  const [note, setNote] = useState('')
  const [reviewError, setReviewError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  useEffect(() => {
    if (!question?.mock_slug || !question?.id) return undefined
    let active = true
    apiFetch(`/api/reviews/${encodeURIComponent(question.mock_slug)}/${encodeURIComponent(question.id)}`)
      .then((data) => {
        if (active) {
          setReview(Object.keys(data).length ? data : null)
          setNote(data.note || '')
        }
      })
      .catch((error) => {
        if (active) setReviewError(error.message)
      })
    return () => { active = false }
  }, [question?.id, question?.mock_slug])

  async function saveReview(nextStatus = review?.status || 'learning') {
    setSaving(true)
    setReviewError('')
    try {
      const saved = await apiFetch(`/api/reviews/${encodeURIComponent(question.mock_slug)}/${encodeURIComponent(question.id)}`, {
        method: 'PUT',
        body: JSON.stringify({ status: nextStatus, note }),
      })
      setReview(saved)
      onReviewSaved?.(saved)
    } catch (error) {
      setReviewError(error.message)
    } finally {
      setSaving(false)
    }
  }

  if (!question) return null
  const status = !question.is_attempted ? 'Skipped' : question.is_correct ? 'Correct' : 'Incorrect'

  return createPortal(
    <div className="modal-backdrop question-backdrop" role="presentation" onMouseDown={onClose}>
      <article className="question-modal" role="dialog" aria-modal="true" aria-labelledby="question-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="question-header">
          <div>
            <p className="eyebrow">{question.mock_title} / {question.section_title}</p>
            <h2 id="question-title">Question {question.number}</h2>
          </div>
          <div className="question-meta"><Badge tone={question.difficulty === 'A' ? 'green' : question.difficulty === 'C' ? 'coral' : 'amber'}>Type {question.difficulty}</Badge><Badge>{question.question_type}</Badge><span><Clock3 size={14} /> {question.time_taken || 0}s</span></div>
          <button className="icon-button" type="button" onClick={onClose} title="Close question"><X size={20} aria-hidden="true" /><span className="sr-only">Close</span></button>
        </header>

        <div className="question-scroll">
          <SafeHtml html={question.question_html} className="question-prompt" />
          {question.options?.length > 0 && (
            <div className="option-list">
              {question.options.map((option, index) => <div className={`option-row ${option.is_correct ? 'is-answer' : ''}`} key={option.id || index}><span>{String.fromCharCode(65 + index)}</span><SafeHtml html={option.html} /></div>)}
            </div>
          )}

          <div className="answer-strip">
            <div>{question.is_correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}<span><small>Outcome</small><strong>{status} ({question.score > 0 ? '+' : ''}{question.score})</strong></span></div>
            <div><span><small>Your answer</small><strong>{answerLabel(question.candidate_answer)}</strong></span></div>
            <div><span><small>Correct answer</small><strong>{answerLabel(question.correct_answer)}</strong></span></div>
          </div>

          {revealSolution && (
            <section className="solution-block">
              <div className="solution-title"><Lightbulb size={18} /><h3>Official solution</h3></div>
              {question.solution_html ? <SafeHtml html={question.solution_html} /> : <p className="muted-copy">No solution text was present in the IMS payload.</p>}
            </section>
          )}

          <section className="review-panel">
            <header><div><CalendarClock size={18} /><h3>Review loop</h3></div>{review && <span>Reviewed {review.review_count}x / next {new Date(review.next_review_at).toLocaleDateString()}</span>}</header>
            <p>Choose how soon this question should return. Saving a status also saves your note.</p>
            <div className="review-actions">
              <button className={review?.status === 'again' ? 'is-selected' : ''} type="button" disabled={saving} onClick={() => saveReview('again')}><RotateCcw size={16} /><span><strong>Again</strong><small>Tomorrow</small></span></button>
              <button className={review?.status === 'learning' ? 'is-selected' : ''} type="button" disabled={saving} onClick={() => saveReview('learning')}><BookOpenCheck size={16} /><span><strong>Learning</strong><small>In 3 days</small></span></button>
              <button className={review?.status === 'mastered' ? 'is-selected' : ''} type="button" disabled={saving} onClick={() => saveReview('mastered')}><CheckCircle2 size={16} /><span><strong>Mastered</strong><small>In 14 days</small></span></button>
            </div>
            <label htmlFor="review-note">Your mistake note</label>
            <textarea id="review-note" value={note} onChange={(event) => setNote(event.target.value)} rows={3} maxLength={2000} placeholder="What fooled you? What rule will you use next time?" />
            <footer>{reviewError ? <span className="form-error">{reviewError}</span> : <span>{review ? `${review.status} / ${review.interval_days}-day interval` : 'Not scheduled yet'}</span>}<button className="button button-ghost" type="button" disabled={saving} onClick={() => saveReview()}>{saving ? <LoaderCircle className="spin" size={15} /> : <Save size={15} />} Save note</button></footer>
          </section>
        </div>
      </article>
    </div>,
    document.body,
  )
}