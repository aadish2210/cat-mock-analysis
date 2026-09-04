import { useState } from 'react'
import { CheckCircle2, FileDown, LoaderCircle, LockKeyhole, X } from 'lucide-react'

import { apiFetch } from '../api'

export default function ImportModal({ onClose, onImported }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const urls = value.split(/\r?\n/).map((url) => url.trim()).filter(Boolean)
    if (!urls.length) {
      setError('Paste at least one IMS View Solutions link.')
      return
    }
    setLoading(true)
    setError('')
    const imported = []
    try {
      for (const url of urls) {
        imported.push(await apiFetch('/api/mocks/import', { method: 'POST', body: JSON.stringify({ url }) }))
      }
      setValue('')
      setResult(imported)
      onImported(imported)
    } catch (requestError) {
      setError(`${imported.length} imported before stopping. ${requestError.message}`)
      if (imported.length) onImported(imported)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="import-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <div className="modal-symbol"><FileDown size={22} aria-hidden="true" /></div>
          <div><p className="eyebrow">Secure local import</p><h2 id="import-title">Add IMS attempts</h2></div>
          <button className="icon-button" type="button" onClick={onClose} title="Close import dialog"><X size={20} aria-hidden="true" /><span className="sr-only">Close</span></button>
        </header>
        {result ? (
          <div className="import-success" role="status"><CheckCircle2 size={34} aria-hidden="true" /><h3>{result.length} {result.length === 1 ? 'mock' : 'mocks'} imported</h3><p>{result.map((mock) => mock.title).join(', ')}</p><button className="button button-primary" type="button" onClick={onClose}>View analysis</button></div>
        ) : (
          <form onSubmit={submit}>
            <label className="field-label" htmlFor="ims-links">View Solutions links</label>
            <textarea id="ims-links" value={value} onChange={(event) => setValue(event.target.value)} placeholder={'https://test-player.imsindia.com/?token=...\nhttps://test-player.imsindia.com/?token=...'} rows={6} autoFocus autoComplete="off" spellCheck="false" />
            <p className="field-help">Paste one link per line. Fresh links work best.</p>
            <div className="privacy-note"><LockKeyhole size={17} aria-hidden="true" /><span>The links exist only in memory during import. Tokens and URLs are never written to disk.</span></div>
            {error && <p className="form-error" role="alert">{error}</p>}
            <footer className="modal-actions"><button className="button button-ghost" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={17} aria-hidden="true" /> : <FileDown size={17} aria-hidden="true" />}{loading ? 'Importing' : 'Import links'}</button></footer>
          </form>
        )}
      </section>
    </div>
  )
}