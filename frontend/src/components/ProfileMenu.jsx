import { useEffect, useRef, useState } from 'react'
import { LogOut, UserRound, X } from 'lucide-react'

import { useApi } from '../api'
import { useAuth } from '../auth-context'

function initials(value) {
  return String(value || 'C').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

export default function ProfileMenu() {
  const { config, user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)
  const profile = useApi('/api/auth/me', user?.id || '')
  const displayName = profile.data?.display_name || user?.user_metadata?.full_name || user?.email || 'Candidate'

  useEffect(() => {
    if (!open) return undefined

    function closeOnOutsideClick(event) {
      if (!menuRef.current?.contains(event.target)) setOpen(false)
    }

    document.addEventListener('pointerdown', closeOnOutsideClick)
    return () => document.removeEventListener('pointerdown', closeOnOutsideClick)
  }, [open])

  async function handleSignOut() {
    setOpen(false)
    await signOut()
  }

  return (
    <div className="profile-menu" ref={menuRef}>
      <button className="profile-trigger" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open} title="Account menu"><span>{initials(displayName)}</span><div><strong>{displayName}</strong><small>{config.mode === 'supabase' ? 'Cloud profile' : 'Local profile'}</small></div></button>
      {open && <div className="profile-popover">
        <header><div><UserRound size={17} /><span><strong>{displayName}</strong><small>{user?.email}</small></span></div><button type="button" onClick={() => setOpen(false)} title="Close account menu"><X size={16} /></button></header>
        {config.auth_enabled && <button className="profile-signout" type="button" onClick={handleSignOut}><LogOut size={16} /><span><strong>Sign out</strong><small>Keep this device data private</small></span></button>}
      </div>}
    </div>
  )
}