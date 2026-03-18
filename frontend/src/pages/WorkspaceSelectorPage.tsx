import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMe, useWorkspaceMembers } from '../hooks/useWorkspace'
import { useAuth } from '../context/AuthContext'
import WorkspaceManagementDrawer from '../components/workspace/WorkspaceManagementDrawer'
import type { WorkspaceInfo } from '../lib/workspaceApi'

function useMyRole(workspaceId: string | null, myUserId: string | undefined): 'OWNER' | 'MEMBER' | 'READ_ONLY' | null {
  const { data: members = [] } = useWorkspaceMembers(workspaceId ?? undefined)
  if (!workspaceId || !myUserId) return null
  return (members.find((m) => m.user_id === myUserId)?.role ?? null) as 'OWNER' | 'MEMBER' | 'READ_ONLY' | null
}

function OverviewButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors text-sm"
      title="Vue d'ensemble du patrimoine"
    >
      ↗
    </button>
  )
}

function ManageButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors text-sm"
      title="Gérer le workspace"
    >
      ⚙
    </button>
  )
}

export default function WorkspaceSelectorPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { data: me, isLoading } = useMe()
  const [managingWorkspace, setManagingWorkspace] = useState<WorkspaceInfo | null>(null)

  const handleSelect = (workspaceId: string) => {
    navigate(`/select-profile?workspace_id=${workspaceId}`)
  }

  const managingRole = useMyRole(managingWorkspace?.id ?? null, me?.id)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg">

        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">DashMoney</h1>
          <p className="text-sm text-gray-400 mt-1">Choisissez un workspace</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
          </div>
        ) : !me?.workspaces.length ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-sm">Aucun workspace disponible.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {me.workspaces.map((ws) => (
              <div
                key={ws.id}
                className="w-full flex items-center bg-white border border-gray-200 rounded-2xl px-6 py-5 hover:border-gray-400 hover:shadow-sm transition-all group"
              >
                <button
                  onClick={() => handleSelect(ws.id)}
                  className="flex-1 flex items-center justify-between text-left min-w-0"
                >
                  <div className="min-w-0">
                    <p className="text-base font-semibold text-gray-900">{ws.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {ws.profiles.length} profil{ws.profiles.length > 1 ? 's' : ''}
                    </p>
                  </div>
                  <span className="text-gray-300 group-hover:text-gray-600 transition-colors text-lg mr-3">→</span>
                </button>
                <OverviewButton onClick={() => navigate(`/workspaces/${ws.id}/overview`)} />
                <ManageButton onClick={() => setManagingWorkspace(ws)} />
              </div>
            ))}
          </div>
        )}

        {/* Infos user + logout */}
        {me && (
          <div className="mt-8 flex items-center justify-between text-xs text-gray-400">
            <span>{me.email}</span>
            <button
              onClick={logout}
              className="hover:text-gray-700 transition-colors"
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
