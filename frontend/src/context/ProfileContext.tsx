import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { setProfileId } from '../lib/api'

const STORAGE_KEY = 'dashmoney_profile'

interface StoredProfile {
  profileId: string
  profileName: string
  workspaceName: string
}

interface ProfileState {
  profileId: string | null
  profileName: string | null
  workspaceName: string | null
  selectProfile: (profileId: string, profileName: string, workspaceName: string) => void
  clearProfile: () => void
}

function loadStored(): StoredProfile | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const ProfileContext = createContext<ProfileState | null>(null)

export function ProfileProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  // Lazy initializer : loadStored() appelé une seule fois au montage
  const [profileId, setProfileIdState] = useState<string | null>(
    () => loadStored()?.profileId ?? null
  )
  const [profileName, setProfileName] = useState<string | null>(
    () => loadStored()?.profileName ?? null
  )
  const [workspaceName, setWorkspaceName] = useState<string | null>(
    () => loadStored()?.workspaceName ?? null
  )

  // Synchronise l'intercepteur axios une seule fois au montage
  useEffect(() => {
    const stored = loadStored()
    if (stored?.profileId) setProfileId(stored.profileId)
  }, [])

  const selectProfile = (pid: string, pname: string, wname: string) => {
    setProfileId(pid)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ profileId: pid, profileName: pname, workspaceName: wname }))
    // Vider tout le cache avant de mettre à jour le state
    // pour que les composants re-fetchent avec le nouveau profil
    queryClient.clear()
    setProfileIdState(pid)
    setProfileName(pname)
    setWorkspaceName(wname)
  }

  const clearProfile = () => {
    setProfileId(null)
    localStorage.removeItem(STORAGE_KEY)
    queryClient.clear()
    setProfileIdState(null)
    setProfileName(null)
    setWorkspaceName(null)
  }

  return (
    <ProfileContext.Provider value={{ profileId, profileName, workspaceName, selectProfile, clearProfile }}>
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfile(): ProfileState {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within ProfileProvider')
  return ctx
}
