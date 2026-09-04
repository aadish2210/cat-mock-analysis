import { useState } from 'react'
import { Ban, Calculator, Clock3, Play, ShieldCheck, SlidersHorizontal } from 'lucide-react'

import { apiFetch, useApi } from '../api'
import { formatNumber } from '../utils'
import { EmptyState, ErrorView, LoadingView, MetricStrip, SectionHeading } from './Ui'

const BLACKLISTS = ['P&C', 'Pipes & Cisterns']

export default function WhatIfSimulatorTab({ refreshKey, onImport }) {
  const mocks = useApi('/api/mocks', refreshKey)
  const [mockSlug, setMockSlug] = useState('')
  const [timeCap, setTimeCap] = useState(180)
  const [blacklists, setBlacklists] = useState([])
  const [immunity, setImmunity] = useState(true)
  const [rate, setRate] = useState(50)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [running, setRunning] = useState(false)

  if (mocks.loading) return <LoadingView label="Loading simulator inputs" />
  if (mocks.error) return <ErrorView message={mocks.error} />
  if (!mocks.data?.length) return <><SectionHeading eyebrow="What-if simulator" title="Test the rules before test day" description="A deterministic replay of time caps, topic exits, trap immunity, and Type A conversion." /><EmptyState title="No attempt to simulate" message="Import at least one IMS mock to create a factual baseline." onImport={onImport} /></>

  function toggleBlacklist(topic) {
    setBlacklists((current) => current.includes(topic) ? current.filter((item) => item !== topic) : [...current, topic])
  }

  async function runSimulation() {
    setRunning(true)
    setError('')
    try {
      setResult(await apiFetch('/api/simulator/run', {
        method: 'POST',
        body: JSON.stringify({ mock_slug: mockSlug || null, time_cap_seconds: timeCap, topic_blacklists: blacklists, type_c_immunity: immunity, type_a_conversion_rate: rate / 100 }),
      }))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setRunning(false)
    }
  }

  const gain = result ? result.simulated_score - result.actual_score : 0
  return (
    <div className="view-stack">
      <SectionHeading eyebrow="What-if simulator" title="Test the rules before test day" description="A deterministic replay of time caps, topic exits, trap immunity, and Type A conversion." action={<button className="button button-primary" type="button" onClick={runSimulation} disabled={running}><Play size={16} fill="currentColor" /> {running ? 'Running' : 'Run simulation'}</button>} />

      <section className="control-surface">
        <div className="control-block"><label><Clock3 size={16} /> Cut-loss time cap</label><div className="segmented-control">{[120, 150, 180].map((seconds) => <button className={timeCap === seconds ? 'is-selected' : ''} type="button" key={seconds} onClick={() => setTimeCap(seconds)}>{seconds / 60}:00</button>)}</div></div>
        <div className="control-block"><label htmlFor="sim-mock"><Calculator size={16} /> Attempt scope</label><select id="sim-mock" value={mockSlug} onChange={(event) => setMockSlug(event.target.value)}><option value="">All imported mocks</option>{mocks.data.map((mock) => <option value={mock.slug} key={mock.slug}>{mock.title}</option>)}</select></div>
        <div className="control-block control-wide"><label><Ban size={16} /> Topic blacklists</label><div className="check-row">{BLACKLISTS.map((topic) => <label className="check-control" key={topic}><input type="checkbox" checked={blacklists.includes(topic)} onChange={() => toggleBlacklist(topic)} /><span>{topic}</span></label>)}</div></div>
        <div className="control-block"><label><ShieldCheck size={16} /> Type C immunity</label><button className={`toggle-control ${immunity ? 'is-on' : ''}`} type="button" role="switch" aria-checked={immunity} onClick={() => setImmunity((value) => !value)}><span /><strong>{immunity ? 'On' : 'Off'}</strong></button></div>
        <div className="control-block control-wide"><label htmlFor="conversion"><SlidersHorizontal size={16} /> Type A conversion <strong>{rate}%</strong></label><input id="conversion" type="range" min="0" max="100" step="10" value={rate} onChange={(event) => setRate(Number(event.target.value))} /></div>
      </section>

      {error && <ErrorView message={error} />}
      {!result && !error && <div className="simulation-standby"><Calculator size={23} /><span>Controls ready</span></div>}
      {result && <>
        <MetricStrip metrics={[
          { label: 'Actual score', value: formatNumber(result.actual_score) },
          { label: 'Simulated score', value: formatNumber(result.simulated_score), tone: 'tone-green', detail: `+${formatNumber(gain)} net gain` },
          { label: 'Penalties avoided', value: `+${formatNumber(result.penalties_saved)}`, tone: 'tone-coral' },
          { label: 'Time released', value: formatNumber(result.freed_minutes, ' min'), tone: 'tone-amber', detail: `+${formatNumber(result.conversion_gain)} converted marks` },
        ]} />
        <section className="data-section"><div className="data-section-title"><div><Calculator size={19} /><h2>Mock-by-mock projection</h2></div><span>Same rules applied independently</span></div><div className="table-wrap"><table><thead><tr><th>Mock</th><th>Actual</th><th>Simulated</th><th>Gain</th><th>Freed time</th></tr></thead><tbody>{result.mocks.map((mock) => <tr key={mock.slug}><td><strong>{mock.title}</strong></td><td className="mono">{mock.actual_score}</td><td className="mono tone-green">{mock.simulated_score}</td><td className="mono">+{formatNumber(mock.simulated_score - mock.actual_score)}</td><td className="mono">{mock.freed_minutes} min</td></tr>)}</tbody></table></div></section>
      </>}
    </div>
  )
}