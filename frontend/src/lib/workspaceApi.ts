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
  role: 'OWNER' | 'MEMBER'
}

export const workspaceApi = {
  me: (): Promise<MeData> =>
    api.get<MeData>('/me').then((r: AxiosResponse<MeData>) => r.data),

  listMembers: (workspaceId: string): Promise<WorkspaceMember[]> =>
    api
      .get<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`)
      .then((r: AxiosResponse<WorkspaceMember[]>) => r.data),

  invite: (workspaceId: string, email: string): Promise<WorkspaceMember> =>
    api
      .post<WorkspaceMember>(`/workspaces/${workspaceId}/members/invite`, { email })
      .then((r: AxiosResponse<WorkspaceMember>) => r.data),

  removeMember: (workspaceId: string, userId: string): Promise<void> =>
    api.delete(`/workspaces/${workspaceId}/members/${userId}`).then(() => undefined),
}
