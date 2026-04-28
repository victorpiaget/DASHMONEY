import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMe, useWorkspaceMembers } from '../hooks/useWorkspace'
import { useAuth } from '../context/AuthContext'
import { useProfile } from '../context/ProfileContext'
import WorkspaceManagementDrawer from '../components/workspace/WorkspaceManagementDrawer'
import ThemeToggle from '../components/ThemeToggle'
import type { WorkspaceInfo } from '../lib/workspaceApi'

function useMyRole(workspaceId: string | null, myUserId: string | undefined): 'OWNER' | 'MEMBER' | 'READ_ONLY' | null {
  const { data: members = [] } = useWorkspaceMembers(workspaceId ?? undefined)
  if (!workspaceId || !myUserId) return null
  return (members.find((m) => m.user_id === myUserId)?.role ?? null) as 'OWNER' | 'MEMBER' | 'READ_ONLY' | null
}

function ManageButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-sm"
      title="Gérer le workspace"
    >
      ⚙
    </button>
  )
}

export default function WorkspaceSelectorPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { selectProfile } = useProfile()
  const { data: me, isLoading } = useMe()
  const [managingWorkspace, setManagingWorkspace] = useState<WorkspaceInfo | null>(null)

  // Auto-sélection si un seul workspace avec un seul profil
  useEffect(() => {
    if (!me || isLoading) return
    if (me.workspaces.length === 1 && me.workspaces[0].profiles.length === 1) {
      const ws = me.workspaces[0]
      const profile = ws.profiles[0]
      selectProfile(profile.id, profile.display_name, ws.name)
      navigate('/', { replace: true })
    }
  }, [me, isLoading, selectProfile, navigate])

  const handleSelect = (workspaceId: string) => {
    navigate(`/select-profile?workspace_id=${workspaceId}`)
  }

  const managingRole = useMyRole(managingWorkspace?.id ?? null, me?.id)

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg">

        {/* Logo */}
        <div className="text-center mb-12 relative">
          <div className="absolute right-0 top-0">
            <ThemeToggle />
          </div>
          <div className="flex justify-center mb-4">
            <div className="w-10 h-10 rounded-xl bg-gray-900 dark:bg-gray-100 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
            </div>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-white">DashMoney</h1>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Choisissez un workspace</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-gray-200 dark:border-gray-700 border-t-gray-700 dark:border-t-gray-300 rounded-full animate-spin" />
          </div>
        ) : !me?.workspaces.length ? (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">
            <p className="text-sm">Aucun workspace disponible.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {me.workspaces.map((ws) => (
              <div
                key={ws.id}
                className="w-full bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-sm transition-all group"
              >
                {/* Sélection du profil */}
                <div className="flex items-center px-6 py-5">
                  <button
                    onClick={() => handleSelect(ws.id)}
                    className="flex-1 flex items-center justify-between text-left min-w-0"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">{ws.name}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        {ws.profiles.length} profil{ws.profiles.length > 1 ? 's' : ''} · Sélectionner un profil
                      </p>
                    </div>
                    <span className="text-gray-300 dark:text-gray-600 group-hover:text-gray-600 dark:group-hover:text-gray-400 transition-colors text-lg mr-3">→</span>
                  </button>
                  <ManageButton onClick={() => setManagingWorkspace(ws)} />
                </div>
                {/* Vue d'ensemble */}
                <div className="border-t border-gray-100 dark:border-gray-800">
                  <button
                    onClick={() => navigate(`/workspaces/${ws.id}/overview`)}
                    className="w-full flex items-center justify-between px-6 py-2.5 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
                  >
                    <span>Vue d'ensemble du patrimoine</span>
                    <span>↗</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Infos user + logout */}
        {me && (
          <div className="mt-8 flex items-center justify-between text-xs text-gray-400 dark:text-gray-500">
            <span>{me.email}</span>
            <button
              onClick={logout}
              className="hover:text-gray-700 dark:hover:text-gray-400 transition-colors"
            >
              Déconnexion
            </button>
          </div>
        )}
      </div>

      {managingWorkspace && me && (
        <WorkspaceManagementDrawer
          workspace={managingWorkspace}
          myUserId={me.id}
          myRole={managingRole}
          onClose={() => setManagingWorkspace(null)}
        />
      )}
    </div>
  )
}
