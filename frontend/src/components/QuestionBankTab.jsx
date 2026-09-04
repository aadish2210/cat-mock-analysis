import { useDeferredValue, useState } from 'react'
import { Eye, Search } from 'lucide-react'

import { apiFetch, useApi } from '../api'
import { Badge, EmptyState, ErrorView, LoadingView, SectionHeading } from './Ui'
import QuestionModal from './QuestionModal'

function plainText(html) {
  return String(html || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

export default function QuestionBankTab({ refreshKey, onImport }) {
  const { data, error, loading } = useApi('/api/questions', refreshKey)
  const [search, setSearch] = useState('')
  const [section, setSection] = useState('all')
  const [difficulty, setDifficulty] = useState('all')
  const [outcome, setOutcome] = useState('all')
  const [limit, setLimit] = useState(50)
  const [openQuestion, setOpenQuestion] = useState(null)
  const [openError, setOpenError] = useState('')
  const deferredSearch = useDeferredValue(search).toLocaleLowerCase()
  if (loading) return <LoadingView label="Indexing question bank" />
  if (error) return <ErrorView message={error} />
  if (!data?.length) return <><SectionHeading eyebrow="Question bank" title="Every attempt, searchable" description="A normalized archive of prompts, outcomes, telemetry, and official solutions." /><EmptyState title="The archive is empty" message="Imported mocks will populate this repository automatically." onImport={onImport} /></>

  const filtered = data.filter((question) => {
    const matchesSearch = !deferredSearch || `${question.topic} ${question.sub_topic} ${question.mock_title} ${question.preview}`.toLocaleLowerCase().includes(deferredSearch)
    const matchesSection = section === 'all' || question.section_slug === section
    const matchesDifficulty = difficulty === 'all' || question.difficulty === difficulty
    const questionOutcome = !question.is_attempted ? 'skipped' : question.is_correct ? 'correct' : 'incorrect'
    return matchesSearch && matchesSection && matchesDifficulty && (outcome === 'all' || outcome === questionOutcome)
  })

  async function openFullQuestion(question) {
    setOpenError('')
    try {
      setOpenQuestion(await apiFetch(`/api/mocks/${encodeURIComponent(question.mock_slug)}/questions/${encodeURIComponent(question.id)}`))
    } catch (requestError) {
      setOpenError(requestError.message)
    }
  }

  return (
    <div className="view-stack">
      <SectionHeading eyebrow="Question bank" title="Every attempt, searchable" description="A normalized archive of prompts, outcomes, telemetry, and official solutions." />
      <div className="filter-bar">
        <label className="search-field"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search topic, mock, or question text" /></label>
        <select value={section} onChange={(event) => setSection(event.target.value)} aria-label="Section filter"><option value="all">All sections</option><option value="varc">VARC</option><option value="dilr">DILR</option><option value="qa">Quants</option></select>
        <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} aria-label="Difficulty filter"><option value="all">All types</option><option value="A">Type A</option><option value="B">Type B</option><option value="C">Type C</option></select>
        <select value={outcome} onChange={(event) => setOutcome(event.target.value)} aria-label="Outcome filter"><option value="all">All outcomes</option><option value="correct">Correct</option><option value="incorrect">Incorrect</option><option value="skipped">Skipped</option></select>
      </div>
      <div className="bank-summary"><span>{filtered.length} matches</span><span>{data.length} total questions</span></div>
      {openError && <ErrorView message={openError} />}
      <div className="question-table table-wrap"><table><thead><tr><th>Question</th><th>Mock / section</th><th>Topic</th><th>Type</th><th>Outcome</th><th>Time</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{filtered.slice(0, limit).map((question, index) => { const status = !question.is_attempted ? 'Skipped' : question.is_correct ? 'Correct' : 'Incorrect'; return <tr key={`${question.mock_slug}-${question.section_slug}-${question.id}-${index}`}><td><strong>Q{question.number}</strong><small>{plainText(question.preview).slice(0, 90)}</small></td><td><strong>{question.mock_title}</strong><small>{question.section_slug.toUpperCase()}</small></td><td>{question.topic}</td><td><Badge tone={question.difficulty === 'A' ? 'green' : question.difficulty === 'C' ? 'coral' : 'amber'}>{question.difficulty}</Badge></td><td><span className={`outcome outcome-${status.toLowerCase()}`}>{status}</span></td><td className="mono">{question.time_taken}s</td><td><button className="icon-button" type="button" title="Open question" onClick={() => openFullQuestion(question)}><Eye size={16} /><span className="sr-only">Open question {question.number}</span></button></td></tr> })}</tbody></table></div>
      {filtered.length > limit && <button className="button button-ghost load-more" type="button" onClick={() => setLimit((current) => current + 50)}>Show 50 more</button>}
      {!filtered.length && <div className="inline-empty">No questions match these filters.</div>}
      {openQuestion && <QuestionModal question={openQuestion} onClose={() => setOpenQuestion(null)} />}
    </div>
  )
}