import { useState } from 'react'
import DOMPurify from 'dompurify'
import { ArrowLeft, ArrowRight, Check, Eye, RotateCcw, Sparkles, X } from 'lucide-react'

import { useApi } from '../api'
import { Badge, EmptyState, ErrorView, LoadingView, SectionHeading } from './Ui'

function normalize(value) {
  return String(value ?? '').replace(/<[^>]*>/g, '').trim().replace(/\s+/g, ' ').toLocaleLowerCase()
}

function acceptedAnswers(question) {
  const answers = []
  const given = question.correct_answer
  if (Array.isArray(given)) answers.push(...given)
  else if (given !== null && given !== undefined && given !== '') answers.push(given)
  question.options?.forEach((option, index) => {
    if (option.is_correct) answers.push(option.id, option.html, String.fromCharCode(65 + index))
  })
  return answers.map(normalize).filter(Boolean)
}

function isCorrectAnswer(answer, question) {
  const normalizedAnswer = normalize(answer)
  return acceptedAnswers(question).some((accepted) => {
    const answerNumber = Number(normalizedAnswer)
    const acceptedNumber = Number(accepted)
    if (normalizedAnswer && Number.isFinite(answerNumber) && Number.isFinite(acceptedNumber)) return Math.abs(answerNumber - acceptedNumber) < 1e-9
    return normalizedAnswer === accepted
  })
}

export default function QuantsDrillTab({ refreshKey, onImport }) {
  const { data, error, loading } = useApi('/api/questions?section=qa&difficulty=A&include_content=1', refreshKey)
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [checked, setChecked] = useState(false)
  const [solutionOpen, setSolutionOpen] = useState(false)
  if (loading) return <LoadingView label="Loading re-solve queue" />
  if (error) return <ErrorView message={error} />
  const questions = data?.filter((question) => !question.is_attempted || !question.is_correct) || []
  if (!questions.length) return <><SectionHeading eyebrow="Quants re-solve lab" title="Missed Type A queue" description="In-browser practice for empirically convertible Quants questions." /><EmptyState title="No missed Quants bankers" message="Import more attempts, or keep the clean conversion record." onImport={!data?.length ? onImport : undefined} /></>
  const safeIndex = Math.min(index, questions.length - 1)
  const question = questions[safeIndex]
  const canCheck = acceptedAnswers(question).length > 0
  const correct = checked && isCorrectAnswer(answer, question)

  function move(direction) {
    setIndex((current) => Math.max(0, Math.min(questions.length - 1, current + direction)))
    setAnswer('')
    setChecked(false)
    setSolutionOpen(false)
  }

  return (
    <div className="view-stack">
      <SectionHeading eyebrow="Quants re-solve lab" title="Missed Type A queue" description="In-browser practice for empirically convertible Quants questions." />
      <div className="drill-progress"><div><span style={{ width: `${((safeIndex + 1) / questions.length) * 100}%` }} /></div><strong>{safeIndex + 1} / {questions.length}</strong></div>
      <section className="drill-workspace">
        <header><div><Badge tone="green">Type A</Badge><Badge>{question.question_type}</Badge><span>{question.topic}</span></div><small>{question.mock_title} / Q{question.number}</small></header>
        <div className="drill-question rich-content" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(String(question.question_html || '')) }} />
        {question.options?.length > 0 && <div className="drill-options">{question.options.map((option, optionIndex) => <button type="button" className={answer === option.id ? 'is-selected' : ''} onClick={() => { setAnswer(option.id); setChecked(false) }} key={option.id}><span>{String.fromCharCode(65 + optionIndex)}</span><div className="rich-content" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(String(option.html || '')) }} /></button>)}</div>}
        <div className="answer-entry"><label htmlFor="drill-answer">Your answer</label><div><input id="drill-answer" value={answer} onChange={(event) => { setAnswer(event.target.value); setChecked(false) }} placeholder="Enter a value or option" /><button className="button button-primary" type="button" disabled={!answer || !canCheck} onClick={() => setChecked(true)}><Check size={16} /> Check</button></div>{!canCheck && <small>IMS did not provide a machine-readable answer for this question.</small>}</div>
        {checked && <div className={`drill-feedback ${correct ? 'is-correct' : 'is-wrong'}`}>{correct ? <Check size={19} /> : <X size={19} />}<div><strong>{correct ? 'Correct conversion' : 'Not yet'}</strong><span>{correct ? 'Bank the method and move.' : 'Review the setup, then inspect the official solution.'}</span></div></div>}
        {solutionOpen && <section className="drill-solution"><h3><Sparkles size={17} /> Official solution</h3><div className="rich-content" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(String(question.solution_html || 'No solution was included.')) }} /></section>}
        <footer><button className="button button-ghost" type="button" onClick={() => move(-1)} disabled={safeIndex === 0}><ArrowLeft size={16} /> Previous</button><button className="button button-ghost" type="button" onClick={() => { setAnswer(''); setChecked(false) }}><RotateCcw size={16} /> Reset</button><button className="button button-ghost" type="button" onClick={() => setSolutionOpen((open) => !open)}><Eye size={16} /> {solutionOpen ? 'Hide solution' : 'Reveal solution'}</button><button className="button button-primary" type="button" onClick={() => move(1)} disabled={safeIndex === questions.length - 1}>Next <ArrowRight size={16} /></button></footer>
      </section>
    </div>
  )
}