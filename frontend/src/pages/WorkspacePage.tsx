import { useState } from 'react'
import { useMe, useWorkspaceMembers, useInviteMember, useRemoveMember, useCreateWorkspace, useUpdateMemberRole } from '../hooks/useWorkspace'
import type { WorkspaceInfo, WorkspaceMember } from '../lib/workspaceApi'

type WorkspaceRole = 'OWNER' | 'MEMBER' | 'READ_ONLY'

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  OWNER: 'Propriétaire',
  MEMBER: 'Membre',
  READ_ONLY: 'Lecture seule',
}

const ROLE_BADGE_CLASS: Record<WorkspaceRole, string> = {
  OWNER: 'bg-gray-900 text-white',
  MEMBER: 'bg-gray-100 text-gray-600',
  READ_ONLY: 'bg-blue-50 text-blue-600',
}

// ---------------------------------------------------------------------------
// WorkspaceCard
// ---------------------------------------------------------------------------

function WorkspaceCard({
  workspace,
  myUserId,
}: {
  workspace: WorkspaceInfo
  myUserId: string
}) {
  const { data: members = [], isLoading: loadingMembers } = useWorkspaceMembers(workspace.id)
  const invite = useInviteMember(workspace.id)
  const remove = useRemoveMember(workspace.id)
  const updateRole = useUpdateMemberRole(workspace.id)

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<WorkspaceRole>('MEMBER')
  const [inviteError, setInviteError] = useState<string | null>(null)

  const myRole = members.find((m) => m.user_id === myUserId)?.role
  const isOwner = myRole === 'OWNER'

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    setInviteError(null)
    const email = inviteEmail.trim()
    if (!email) return
    try {
      await invite.mutateAsync({ email, role: inviteRole })
      setInviteEmail('')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Erreur lors de l\'invitation'
      setInviteError(msg)
    }
  }

  async function handleRemove(member: WorkspaceMember) {
    if (!confirm(`Révoquer l'accès de ${member.email} ?`)) return
    try {
      await remove.mutateAsync(member.user_id)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Erreur lors de la révocation'
      alert(msg)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
      {/* Header workspace */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-gray-900">{workspace.name}</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {workspace.profiles.length} profil{workspace.profiles.length > 1 ? 's' : ''}
            {myRole && (
              <span className={`ml-2 px-1.5 py-0.5 rounded text-xs font-medium ${
                ROLE_BADGE_CLASS[myRole as WorkspaceRole] ?? 'bg-gray-100 text-gray-600'
              }`}>
                {ROLE_LABELS[myRole as WorkspaceRole] ?? myRole}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Profils */}
      <div className="px-6 py-4 border-b border-gray-100">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Profils</p>
        <div className="flex flex-wrap gap-2">
          {workspace.profiles.map((p) => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg text-sm text-gray-700 border border-gray-100"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 inline-block" />
              {p.display_name}
            </span>
          ))}
        </div>
      </div>

      {/* Membres */}
      <div className="px-6 py-4">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Membres</p>

        {loadingMembers ? (
          <div className="flex items-center justify-center py-4">
            <div className="w-5 h-5 border-2 border-gray-200 border-t-gray-500 rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-1">
            {members.map((m) => (
              <div
                key={m.user_id}
                className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600 flex-shrink-0">
                    {m.email[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{m.email}</p>
                    <p className="text-xs text-gray-400">
                      {m.user_id === myUserId ? 'Vous' : ROLE_LABELS[m.role as WorkspaceRole] ?? m.role}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    ROLE_BADGE_CLASS[m.role as WorkspaceRole] ?? 'bg-gray-100 text-gray-500'
                  }`}>
                    {ROLE_LABELS[m.role as WorkspaceRole] ?? m.role}
                  </span>
                  {isOwner && m.user_id !== myUserId && (
                    <>
                      <select
                        value={m.role}
                        onChange={(e) =>
                          updateRole.mutate({ userId: m.user_id, role: e.target.value as WorkspaceRole })
                        }
                        disabled={updateRole.isPending}
                        className="text-xs border border-gray-200 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-gray-300 disabled:opacity-50"
                      >
                        <option value="OWNER">Propriétaire</option>
                        <option value="MEMBER">Membre</option>
                        <option value="READ_ONLY">Lecture seule</option>
                      </select>
                      <button
                        onClick={() => handleRemove(m)}
                        disabled={remove.isPending}
                        className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 transition-colors disabled:opacity-50"
                      >
                        Révoquer
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Invite form */}
        {isOwner && (
          <form onSubmit={handleInvite} className="mt-4 flex gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => {
                setInviteEmail(e.target.value)
                setInviteError(null)
              }}
              placeholder="email@exemple.com"
              className="flex-1 px-3.5 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300 focus:border-transparent"
              disabled={invite.isPending}
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as WorkspaceRole)}
              disabled={invite.isPending}
              className="px-2 py-2 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gray-300"
            >
              <option value="MEMBER">Membre</option>
              <option value="READ_ONLY">Lecture seule</option>
              <option value="OWNER">Propriétaire</option>
            </select>
            <button
              type="submit"
              disabled={invite.isPending || !inviteEmail.trim()}
              className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {invite.isPending ? 'Invitation…' : 'Inviter'}
            </button>
          </form>
        )}

        {inviteError && (
          <p className="mt-2 text-sm text-red-600">{inviteError}</p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// WorkspacePage
// ---------------------------------------------------------------------------

export default function WorkspacePage() {
  const { data: me, isLoading } = useMe()
  const createWorkspace = useCreateWorkspace()
  const [showNewForm, setShowNewForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const name = newName.trim()
    if (!name) return
    setCreateError(null)
    try {
      await createWorkspace.mutateAsync(name)
      setNewName('')
      setShowNewForm(false)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Erreur lors de la création'
      setCreateError(msg)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Mon espace</h1>
          <p className="text-sm text-gray-500 mt-1">
            Gérez vos workspaces et les accès partagés.
          </p>
        </div>
        <button
          onClick={() => { setShowNewForm(true); setCreateError(null) }}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
        >
          <span className="text-base leading-none">+</span>
          Nouveau workspace
        </button>
      </div>

      {/* Formulaire création */}
      {showNewForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-xl border border-gray-200 px-6 py-5 mb-4 space-y-3"
        >
          <p className="text-sm font-medium text-gray-700">Nom du workspace</p>
          <div className="flex gap-2">
            <input
              type="text"
              required
              autoFocus
              value={newName}
              onChange={(e) => { setNewName(e.target.value); setCreateError(null) }}
              placeholder="Ex : Famille Dupont"
              className="flex-1 px-3.5 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300 focus:border-transparent"
              disabled={createWorkspace.isPending}
            />
            <button
              type="submit"
              disabled={createWorkspace.isPending || !newName.trim()}
              className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {createWorkspace.isPending ? 'Création…' : 'Créer'}
            </button>
            <button
              type="button"
              onClick={() => { setShowNewForm(false); setNewName(''); setCreateError(null) }}
              className="px-3 py-2 text-gray-400 hover:text-gray-600 text-sm"
            >
              ×
            </button>
          </div>
          {createError && (
            <p className="text-sm text-red-600">{createError}</p>
          )}
        </form>
      )}

      {/* User info */}
      {me && (
        <div className="bg-gray-50 rounded-xl px-5 py-4 mb-6 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gray-900 flex items-center justify-center text-white text-sm font-semibold flex-shrink-0">
            {me.email[0].toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">{me.email}</p>
            <p className="text-xs text-gray-400">
              {me.workspaces.length} workspace{me.workspaces.length > 1 ? 's' : ''}
            </p>
          </div>
        </div>
      )}

      {/* Workspaces */}
      <div className="space-y-4">
        {me?.workspaces.map((w) => (
          <WorkspaceCard key={w.id} workspace={w} myUserId={me.id} />
        ))}
        {me?.workspaces.length === 0 && !showNewForm && (
          <p className="text-sm text-gray-400 text-center py-8">Aucun workspace trouvé.</p>
        )}
      </div>
    </div>
  )
}
