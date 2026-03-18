import { useState, useEffect, useRef } from 'react'
import {
  useWorkspaceMembers,
  useInviteMember,
  useRemoveMember,
  useUpdateMemberRole,
  useRenameWorkspace,
  useCreateProfile,
  useRenameProfile,
  useDeleteProfile,
  useLinkProfile,
  useUnlinkProfile,
  useMe,
} from '../../hooks/useWorkspace'
import type { WorkspaceInfo, WorkspaceMember } from '../../lib/workspaceApi'

type WorkspaceRole = 'OWNER' | 'MEMBER' | 'READ_ONLY'

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  OWNER: 'Propriétaire',
  MEMBER: 'Membre',
  READ_ONLY: 'Lecture seule',
}

interface Props {
  workspace: WorkspaceInfo
  myUserId: string
  myRole: WorkspaceRole | null
  onClose: () => void
}

export default function WorkspaceManagementDrawer({ workspace, myUserId, myRole, onClose }: Props) {
  const isOwner = myRole === 'OWNER'

  // Workspace rename
  const renameWorkspace = useRenameWorkspace()
  const [wsName, setWsName] = useState(workspace.name)
  const [wsNameEditing, setWsNameEditing] = useState(false)
  const wsNameRef = useRef<HTMLInputElement>(null)

  // Profile management
  const createProfile = useCreateProfile(workspace.id)
  const renameProfile = useRenameProfile(workspace.id)
  const deleteProfile = useDeleteProfile()
  const [newProfileName, setNewProfileName] = useState('')
  const [showAddProfile, setShowAddProfile] = useState(false)
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null)
  const [editingProfileName, setEditingProfileName] = useState('')

  // Members
  const { data: members = [], isLoading: loadingMembers } = useWorkspaceMembers(workspace.id)
  const invite = useInviteMember(workspace.id)
  const removeMember = useRemoveMember(workspace.id)
  const updateRole = useUpdateMemberRole(workspace.id)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<WorkspaceRole>('MEMBER')
  const [inviteError, setInviteError] = useState<string | null>(null)

  // Profile linking
  const { data: me } = useMe()
  const linkProfile = useLinkProfile(workspace.id)
  const unlinkProfile = useUnlinkProfile(workspace.id)
  const [showLinkProfile, setShowLinkProfile] = useState(false)

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (wsNameEditing && wsNameRef.current) wsNameRef.current.focus()
  }, [wsNameEditing])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleRenameWorkspace() {
    const name = wsName.trim()
    if (!name || name === workspace.name) { setWsNameEditing(false); setWsName(workspace.name); return }
    setError(null)
    try {
      await renameWorkspace.mutateAsync({ workspaceId: workspace.id, name })
      setWsNameEditing(false)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleCreateProfile() {
    const name = newProfileName.trim()
    if (!name) return
    setError(null)
    try {
      await createProfile.mutateAsync(name)
      setNewProfileName('')
      setShowAddProfile(false)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleRenameProfile(profileId: string) {
    const name = editingProfileName.trim()
    if (!name) return
    setError(null)
    try {
      await renameProfile.mutateAsync({ profileId, displayName: name })
      setEditingProfileId(null)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleDeleteProfile(profileId: string, profileName: string) {
    if (!confirm(`Supprimer le profil "${profileName}" ? Cette action est irréversible.`)) return
    setError(null)
    try {
      await deleteProfile.mutateAsync(profileId)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleLinkProfile(profileId: string) {
    setError(null)
    try {
      await linkProfile.mutateAsync(profileId)
      setShowLinkProfile(false)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleUnlinkProfile(profileId: string, profileName: string) {
    if (!confirm(`Délier le profil "${profileName}" de ce workspace ?`)) return
    setError(null)
    try {
      await unlinkProfile.mutateAsync(profileId)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    setInviteError(null)
    const email = inviteEmail.trim()
    if (!email) return
    try {
      await invite.mutateAsync({ email, role: inviteRole })
      setInviteEmail('')
    } catch (e: unknown) {
      setInviteError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  async function handleRemoveMember(member: WorkspaceMember) {
    if (!confirm(`Révoquer l'accès de ${member.email} ?`)) return
    try {
      await removeMember.mutateAsync(member.user_id)
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Erreur')
    }
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-none">
          <h2 className="text-sm font-semibold text-gray-900">Gérer le workspace</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors text-lg leading-none"
          >
            ×
          </button>
        </div>

        {/* Body scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          {/* ── Section : Workspace ── */}
          <section>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Workspace</p>
            <div className="bg-gray-50 rounded-xl px-4 py-3">
              {wsNameEditing ? (
                <div className="flex items-center gap-2">
                  <input
                    ref={wsNameRef}
                    value={wsName}
                    onChange={(e) => setWsName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleRenameWorkspace(); if (e.key === 'Escape') { setWsNameEditing(false); setWsName(workspace.name) } }}
                    className="flex-1 px-2.5 py-1.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                    disabled={renameWorkspace.isPending}
                  />
                  <button
                    onClick={handleRenameWorkspace}
                    disabled={renameWorkspace.isPending}
                    className="px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
                  >
                    {renameWorkspace.isPending ? '…' : 'OK'}
                  </button>
                  <button
                    onClick={() => { setWsNameEditing(false); setWsName(workspace.name) }}
                    className="text-gray-400 hover:text-gray-600 text-sm px-1"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{wsName}</span>
                  {isOwner && (
                    <button
                      onClick={() => setWsNameEditing(true)}
                      className="text-xs text-gray-400 hover:text-gray-700 transition-colors px-2 py-1 rounded hover:bg-gray-200"
                    >
                      Renommer
                    </button>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* ── Section : Profils ── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Profils</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setShowLinkProfile(!showLinkProfile); setShowAddProfile(false) }}
                  className="text-xs text-gray-500 hover:text-gray-900 transition-colors flex items-center gap-1"
                  title="Lier un profil existant"
                >
                  ⇄ Lier
                </button>
                <button
                  onClick={() => { setShowAddProfile(true); setNewProfileName(''); setShowLinkProfile(false) }}
                  className="text-xs text-gray-500 hover:text-gray-900 transition-colors flex items-center gap-1"
                >
                  <span className="text-base leading-none">+</span> Nouveau
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              {workspace.profiles.map((profile) => {
                const isCrossLinked = profile.workspace_id !== workspace.id
                return (
                  <div key={profile.id} className="bg-gray-50 rounded-xl px-4 py-2.5">
                    {editingProfileId === profile.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          autoFocus
                          value={editingProfileName}
                          onChange={(e) => setEditingProfileName(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') handleRenameProfile(profile.id); if (e.key === 'Escape') setEditingProfileId(null) }}
                          className="flex-1 px-2.5 py-1 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                          disabled={renameProfile.isPending}
                        />
                        <button
                          onClick={() => handleRenameProfile(profile.id)}
                          disabled={renameProfile.isPending}
                          className="px-3 py-1 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
                        >
                          {renameProfile.isPending ? '…' : 'OK'}
                        </button>
                        <button onClick={() => setEditingProfileId(null)} className="text-gray-400 hover:text-gray-600 text-sm px-1">×</button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-xs font-semibold text-gray-600 flex-shrink-0">
                            {profile.display_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="text-sm font-medium text-gray-800">{profile.display_name}</span>
                            {isCrossLinked && (
                              <span className="ml-1.5 text-[10px] text-blue-500 font-medium">lié</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {!isCrossLinked && (
                            <button
                              onClick={() => { setEditingProfileId(profile.id); setEditingProfileName(profile.display_name) }}
                              className="text-xs text-gray-400 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-200 transition-colors"
                            >
                              Renommer
                            </button>
                          )}
                          {isCrossLinked ? (
                            <button
                              onClick={() => handleUnlinkProfile(profile.id, profile.display_name)}
                              disabled={unlinkProfile.isPending}
                              className="text-xs text-orange-400 hover:text-orange-600 px-2 py-1 rounded hover:bg-orange-50 transition-colors disabled:opacity-50"
                            >
                              Délier
                            </button>
                          ) : workspace.profiles.length > 1 ? (
                            <button
                              onClick={() => handleDeleteProfile(profile.id, profile.display_name)}
                              disabled={deleteProfile.isPending}
                              className="text-xs text-red-400 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50 transition-colors disabled:opacity-50"
                            >
                              ×
                            </button>
                          ) : null}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}

              {workspace.profiles.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-3">Aucun profil</p>
              )}
            </div>

            {/* Lier un profil existant */}
            {showLinkProfile && (() => {
              const linkedIds = new Set(workspace.profiles.map((p) => p.id))
              const myAllProfiles = me?.workspaces.flatMap((w) => w.profiles) ?? []
              const linkable = myAllProfiles.filter((p) => !linkedIds.has(p.id))
              return (
                <div className="mt-3 bg-blue-50 rounded-xl px-4 py-3">
                  <p className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider mb-2">
                    Lier un de vos profils
                  </p>
                  {linkable.length === 0 ? (
                    <p className="text-xs text-gray-400">Tous vos profils sont déjà dans ce workspace.</p>
                  ) : (
                    <div className="space-y-1">
                      {linkable.map((p) => (
                        <div key={p.id} className="flex items-center justify-between py-1">
                          <div>
                            <span className="text-xs font-medium text-gray-800">{p.display_name}</span>
                            <span className="ml-1.5 text-[10px] text-gray-400">
                              {me?.workspaces.find((w) => w.id === p.workspace_id)?.name}
                            </span>
                          </div>
                          <button
                            onClick={() => handleLinkProfile(p.id)}
                            disabled={linkProfile.isPending}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-0.5 rounded hover:bg-blue-100 transition-colors disabled:opacity-50"
                          >
                            Lier
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <button onClick={() => setShowLinkProfile(false)} className="mt-2 text-[10px] text-gray-400 hover:text-gray-600">
                    Fermer
                  </button>
                </div>
              )
            })()}

            {showAddProfile && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  autoFocus
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleCreateProfile(); if (e.key === 'Escape') setShowAddProfile(false) }}
                  placeholder="Nom du profil"
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
                  disabled={createProfile.isPending}
                />
                <button
                  onClick={handleCreateProfile}
                  disabled={createProfile.isPending || !newProfileName.trim()}
                  className="px-3 py-2 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  {createProfile.isPending ? '…' : 'Créer'}
                </button>
                <button onClick={() => setShowAddProfile(false)} className="text-gray-400 hover:text-gray-600 text-sm px-1">×</button>
              </div>
            )}
          </section>

          {/* ── Section : Membres ── */}
          <section>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Membres</p>

            {loadingMembers ? (
              <div className="flex justify-center py-4">
                <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
              </div>
            ) : (
              <div className="space-y-1">
                {members.map((m) => (
                  <div key={m.user_id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600 flex-shrink-0">
                        {m.email[0].toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">{m.email}</p>
                        <p className="text-[10px] text-gray-400">{m.user_id === myUserId ? 'Vous' : ROLE_LABELS[m.role as WorkspaceRole] ?? m.role}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {isOwner && m.user_id !== myUserId ? (
                        <>
                          <select
                            value={m.role}
                            onChange={(e) => updateRole.mutate({ userId: m.user_id, role: e.target.value as WorkspaceRole })}
                            disabled={updateRole.isPending}
                            className="text-[10px] border border-gray-200 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-gray-300 disabled:opacity-50"
                          >
                            <option value="OWNER">Propriétaire</option>
                            <option value="MEMBER">Membre</option>
                            <option value="READ_ONLY">Lecture seule</option>
                          </select>
                          <button
                            onClick={() => handleRemoveMember(m)}
                            disabled={removeMember.isPending}
                            className="text-[10px] text-red-400 hover:text-red-600 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors disabled:opacity-50"
                          >
                            Révoquer
                          </button>
                        </>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-500">
                          {ROLE_LABELS[m.role as WorkspaceRole] ?? m.role}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {isOwner && (
              <form onSubmit={handleInvite} className="mt-3 space-y-2">
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => { setInviteEmail(e.target.value); setInviteError(null) }}
                    placeholder="email@exemple.com"
                    className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-xs focus:outline-none focus:ring-2 focus:ring-gray-300 focus:border-transparent"
                    disabled={invite.isPending}
                  />
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as WorkspaceRole)}
                    disabled={invite.isPending}
                    className="px-2 py-2 rounded-lg border border-gray-200 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-gray-300"
                  >
                    <option value="MEMBER">Membre</option>
                    <option value="READ_ONLY">Lecture seule</option>
                    <option value="OWNER">Propriétaire</option>
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={invite.isPending || !inviteEmail.trim()}
                  className="w-full py-2 bg-gray-900 text-white text-xs font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {invite.isPending ? 'Invitation…' : 'Inviter un membre'}
                </button>
                {inviteError && <p className="text-xs text-red-600">{inviteError}</p>}
              </form>
            )}
          </section>
        </div>
      </div>
    </>
  )
}
