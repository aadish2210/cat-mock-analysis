import { useEffect, useState } from 'react'

let accessTokenProvider = () => null

export function setAccessTokenProvider(provider) {
  accessTokenProvider = provider || (() => null)
}

export async function apiFetch(path, options = {}) {
  const { headers: providedHeaders, ...requestOptions } = options
  const accessToken = await accessTokenProvider()
  const response = await fetch(path, {
    ...requestOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...providedHeaders,
    },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new Event('cat:auth-expired'))
    }
    const error = new Error(payload.error || `Request failed (${response.status})`)
    error.status = response.status
    error.code = payload.code
    throw error
  }
  return payload
}

export function useApi(path, refreshKey = 0) {
  const requestKey = `${path || ''}:${refreshKey}`
  const [state, setState] = useState({ requestKey: '', data: null, error: '' })

  useEffect(() => {
    if (!path) return undefined

    const controller = new AbortController()
    apiFetch(path, { signal: controller.signal })
      .then((data) => setState({ requestKey, data, error: '' }))
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setState({ requestKey, data: null, error: error.message })
        }
      })

    return () => controller.abort()
  }, [path, requestKey])

  const isCurrent = state.requestKey === requestKey
  return {
    data: isCurrent ? state.data : null,
    error: isCurrent ? state.error : '',
    loading: Boolean(path) && !isCurrent,
  }
}