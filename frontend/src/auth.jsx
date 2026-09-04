import { useEffect, useState } from 'react'

import { setAccessTokenProvider } from './api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [state, setState] = useState({
    config: null,
    client: null,
    session: null,
    user: null,
    loading: true,
    error: '',
  })

  useEffect(() => {
    let active = true
    let subscription

    async function initialize() {
      try {
        const response = await fetch('/api/config', { headers: { Accept: 'application/json' } })
        const config = await response.json()
        if (!response.ok) throw new Error(config.error || 'Could not load application configuration.')
        if (!config.auth_enabled) {
          if (active) setState({ config, client: null, session: null, user: { id: 'local-user', email: 'local@device' }, loading: false, error: '' })
          return
        }

        const { createClient } = await import('@supabase/supabase-js')
        const client = createClient(config.supabase.url, config.supabase.publishable_key, {
          auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
          },
        })
        const { data, error } = await client.auth.getSession()
        if (error) throw error
        setAccessTokenProvider(async () => {
          const { data: sessionData } = await client.auth.getSession()
          return sessionData.session?.access_token || null
        })
        if (active) setState({ config, client, session: data.session, user: data.session?.user || null, loading: false, error: '' })
        subscription = client.auth.onAuthStateChange((_event, session) => {
          if (active) setState((current) => ({ ...current, session, user: session?.user || null, loading: false, error: '' }))
        }).data.subscription
      } catch (error) {
        if (active) setState((current) => ({ ...current, loading: false, error: error.message }))
      }
    }

    initialize()
    return () => {
      active = false
      subscription?.unsubscribe()
      setAccessTokenProvider(null)
    }
  }, [])

  useEffect(() => {
    function expireSession() {
      state.client?.auth.signOut({ scope: 'local' })
    }
    window.addEventListener('cat:auth-expired', expireSession)
    return () => window.removeEventListener('cat:auth-expired', expireSession)
  }, [state.client])

  async function signIn(email, password) {
    const { error } = await state.client.auth.signInWithPassword({ email, password })
    if (error) throw error
  }

  async function signUp(email, password, displayName) {
    const { data, error } = await state.client.auth.signUp({
      email,
      password,
      options: { data: { full_name: displayName } },
    })
    if (error) throw error
    return data
  }

  async function sendMagicLink(email) {
    const { error } = await state.client.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    })
    if (error) throw error
  }

  async function signOut() {
    setState((current) => ({ ...current, session: null, user: null }))
    if (state.client) {
      await state.client.auth.signOut({ scope: 'local' })
    }
  }

  return (
    <AuthContext.Provider value={{ ...state, signIn, signUp, sendMagicLink, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}