import { useState } from 'react'
import { ArrowRight, Eye, EyeOff, Gauge, KeyRound, LoaderCircle, LockKeyhole, Mail, ShieldCheck } from 'lucide-react'

import { useAuth } from '../auth-context'

export default function AuthScreen() {
  const { signIn, signUp, sendMagicLink, error: configurationError } = useAuth()
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function submit(event) {
    event.preventDefault()
    setWorking(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'signin') {
        await signIn(email.trim(), password)
      } else {
        const result = await signUp(email.trim(), password, displayName.trim())
        if (!result.session) setMessage('Account created. Check your email to confirm the address.')
      }
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setWorking(false)
    }
  }

  async function magicLink() {
    if (!email.trim()) {
      setError('Enter your email first.')
      return
    }
    setWorking(true)
    setError('')
    try {
      await sendMagicLink(email.trim())
      setMessage('Magic link sent. You can close this tab after opening the email.')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setWorking(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-context">
        <div className="auth-brand"><span><Gauge size={25} /></span><div><strong>CAT / DIAGNOSTIC</strong><small>Strategic intelligence</small></div></div>
        <div className="auth-statement"><p className="eyebrow">Private performance workspace</p><h1>Your decisions.<br />Your evidence.<br /><span>Your next score.</span></h1><p>Each account keeps its mock attempts, analysis, and revision ledger isolated by database policy.</p></div>
        <div className="auth-trust"><div><ShieldCheck size={17} /><span><strong>Row-level isolation</strong><small>Every query is scoped to the signed-in user.</small></span></div><div><LockKeyhole size={17} /><span><strong>Tokens stay transient</strong><small>IMS links are never stored.</small></span></div></div>
      </section>

      <section className="auth-form-side">
        <form className="auth-form" onSubmit={submit}>
          <header><p className="eyebrow">{mode === 'signin' ? 'Welcome back' : 'New candidate profile'}</p><h2>{mode === 'signin' ? 'Sign in to your workspace' : 'Create your workspace'}</h2></header>
          <div className="auth-tabs"><button type="button" className={mode === 'signin' ? 'is-selected' : ''} onClick={() => setMode('signin')}>Sign in</button><button type="button" className={mode === 'signup' ? 'is-selected' : ''} onClick={() => setMode('signup')}>Create account</button></div>
          {mode === 'signup' && <label className="auth-field"><span>Display name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required minLength={1} maxLength={80} autoComplete="name" placeholder="Your name" /></label>}
          <label className="auth-field"><span>Email</span><div><Mail size={16} /><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" placeholder="you@example.com" /></div></label>
          <label className="auth-field"><span>Password</span><div><KeyRound size={16} /><input type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} placeholder="Minimum 8 characters" /><button type="button" onClick={() => setShowPassword((visible) => !visible)} title={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
          {(error || configurationError) && <p className="auth-error" role="alert">{error || configurationError}</p>}
          {message && <p className="auth-message" role="status">{message}</p>}
          <button className="auth-submit" type="submit" disabled={working}>{working ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}{mode === 'signin' ? 'Enter workspace' : 'Create account'}</button>
          <div className="auth-divider"><span>or</span></div>
          <button className="auth-magic" type="button" disabled={working} onClick={magicLink}><Mail size={16} /> Email me a magic link</button>
        </form>
      </section>
    </main>
  )
}