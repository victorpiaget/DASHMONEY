import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMe, useWorkspaceMembers } from '../hooks/useWorkspace'
import { useProfile } from '../context/ProfileContext'
import WorkspaceManagementDrawer from '../components/workspace/WorkspaceManagementDrawer'
import ThemeToggle from '../components/ThemeToggle'

export default function ProfileSelectorPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const workspaceId = params.get('workspace_id') ?? ''
  const { data: me, isLoading } = useMe()
  const { selectProfile } = useProfile()
  const [showDrawer, setShowDrawer] = useState(false)

  const workspace = me?.workspaces.find((w) => w.id === workspaceId)

  const { data: members = [] } = useWorkspaceMembers(workspaceId || undefined)
  const myRole = me ? ((members.find((m) => m.user_id === me.id)?.role ?? null) as 'OWNER' | 'MEMBER' | 'READ_ONLY' | null) : null

  const handleSelect = (profileId: string, profileName: string) => {
    selectProfile(profileId, profileName, workspace?.name ?? '')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg">

        {/* Logo + fil d'Ariane */}
        <div className="text-center mb-10 relative">
          <div className="absolute right-0 top-0">
            <ThemeToggle />
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">DashMoney</h1>
          {workspace && (
            <div className="flex items-center justify-center gap-2 mt-2">
              <button
                onClick={() => navigate('/select-workspace')}
                className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
              >
                {workspace.name}
              </button>
              <span className="text-gray-300 text-xs">›</span>
              <span className="text-xs text-gray-600 font-medium">Choisissez un profil</span>
              <button
                onClick={() => setShowDrawer(true)}
                className="ml-1 w-6 h-6 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-200 transition-colors text-xs"
                title="Gérer le workspace"
              >
                ⚙
              </button>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-gray-200 border-t-gray-700 rounded-full animate-spin" />
          </div>
        ) : !workspace ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-sm">Workspace introuvable.</p>
            <button onClick={() => navigate('/select-workspace')} className="mt-3 text-xs text-gray-500 hover:text-gray-900 underline">
              Retour
            </button>
          </div>
        ) : workspace.profiles.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-sm">Aucun profil accessible dans ce workspace.</p>
            <button
              onClick={() => setShowDrawer(true)}
              className="mt-3 text-xs text-gray-700 hover:text-gray-900 underline"
            >
              Créer un profil
            </button>
            <br />
            <button onClick={() => navigate('/select-workspace')} className="mt-2 text-xs text-gray-500 hover:text-gray-900 underline">
              Retour
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {workspace.profiles.map((profile) => (
              <button
                key={profile.id}
                onClick={() => handleSelect(profile.id, profile.display_name)}
                className="w-full flex items-center justify-between bg-white border border-gray-200 rounded-2xl px-6 py-5 hover:border-gray-400 hover:shadow-sm transition-all group text-left"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 font-semibold text-sm flex-shrink-0">
                    {profile.display_name.charAt(0).toUpperCase()}
                  </div>
                  <p className="text-base font-semibold text-gray-900">{profile.display_name}</p>
                </div>
                <span className="text-gray-300 group-hover:text-gray-600 transition-colors text-lg">→</span>
              </button>
            ))}
          </div>
        )}

        <div className="mt-8 text-center">
          <button
            onClick={() => navigate('/select-workspace')}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            ← Retour aux workspaces
          </button>
        </div>
      </div>

      {showDrawer && workspace && me && (
        <WorkspaceManagementDrawer
          workspace={workspace}
          myUserId={me.id}
          myRole={myRole}
          onClose={() => setShowDrawer(false)}
        />
      )}
    </div>
  )
}
