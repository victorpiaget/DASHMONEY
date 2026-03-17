import { api } from './api'
import type { AxiosResponse } from 'axios'

export interface WorkspaceProfile {
  id: string
  workspace_id: string
  display_name: string
  created_at: string
}

export interface WorkspaceInfo {
  id: string
  name: string
  created_at: string
  profiles: WorkspaceProfile[]
}

export interface MeData {
  id: string
  email: string
  workspaces: WorkspaceInfo[]
}

export interface WorkspaceMember {
  user_id: string
  email: string
  role: 'OWNER' | 'MEMBER' | 'READ_ONLY'
}

export const workspaceApi = {
  me: (): Promise<MeData> =>
    api.get<MeData>('/me').then((r: AxiosResponse<MeData>) => r.data),

  createWorkspace: (name: string): Promise<{ id: string; name: string; created_at: string }> =>
    api
      .post<{ id: string; name: string; created_at: string }>('/workspaces', { name })
      .then((r: AxiosResponse<{ id: string; name: string; created_at: string }>) => r.data),

  listMembers: (workspaceId: string): Promise<WorkspaceMember[]> =>
    api
      .get<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`)
      .then((r: AxiosResponse<WorkspaceMember[]>) => r.data),

  invite: (workspaceId: string, email: string, role: WorkspaceMember['role'] = 'MEMBER'): Promise<WorkspaceMember> =>
    api
      .post<WorkspaceMember>(`/workspaces/${workspaceId}/members/invite`, { email, role })
      .then((r: AxiosResponse<WorkspaceMember>) => r.data),

  removeMember: (workspaceId: string, userId: string): Promise<void> =>
    api.delete(`/workspaces/${workspaceId}/members/${userId}`).then(() => undefined),

  updateMemberRole: (workspaceId: string, userId: string, role: WorkspaceMember['role']): Promise<WorkspaceMember> =>
    api
      .patch<WorkspaceMember>(`/workspaces/${workspaceId}/members/${userId}`, { role })
      .then((r: AxiosResponse<WorkspaceMember>) => r.data),
}
