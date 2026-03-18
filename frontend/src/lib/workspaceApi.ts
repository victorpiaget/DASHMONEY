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

export interface ProfileNetWorthEntry {
  profile_id: string
  display_name: string
  accounts_eur: string
  portfolios_eur: string
  total_eur: string
}

export interface WorkspaceNetWorth {
  workspace_id: string
  currency: string
  at: string | null
  total_eur: string
  profiles: ProfileNetWorthEntry[]
}

export interface WorkspaceNetWorthPoint {
  bucket: string
  total_eur: string
  by_profile: Record<string, string>
}

export interface WorkspaceNetWorthTimeseries {
  workspace_id: string
  currency: string
  date_from: string
  date_to: string
  granularity: string
  points: WorkspaceNetWorthPoint[]
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

  renameWorkspace: (workspaceId: string, name: string): Promise<{ id: string; name: string; created_at: string }> =>
    api
      .patch<{ id: string; name: string; created_at: string }>(`/workspaces/${workspaceId}`, { name })
      .then((r) => r.data),

  createProfile: (workspaceId: string, displayName: string): Promise<WorkspaceProfile> =>
    api
      .post<WorkspaceProfile>(`/workspaces/${workspaceId}/profiles`, { display_name: displayName })
      .then((r: AxiosResponse<WorkspaceProfile>) => r.data),

  renameProfile: (workspaceId: string, profileId: string, displayName: string): Promise<WorkspaceProfile> =>
    api
      .patch<WorkspaceProfile>(`/workspaces/${workspaceId}/profiles/${profileId}`, { display_name: displayName })
      .then((r: AxiosResponse<WorkspaceProfile>) => r.data),

  deleteProfile: (profileId: string): Promise<void> =>
    api.delete(`/profiles/${profileId}`).then(() => undefined),

  linkProfile: (workspaceId: string, profileId: string): Promise<WorkspaceProfile> =>
    api
      .post<WorkspaceProfile>(`/workspaces/${workspaceId}/profiles/${profileId}/link`)
      .then((r: AxiosResponse<WorkspaceProfile>) => r.data),

  unlinkProfile: (workspaceId: string, profileId: string): Promise<void> =>
    api.delete(`/workspaces/${workspaceId}/profiles/${profileId}/link`).then(() => undefined),

  getWorkspaceNetWorth: (workspaceId: string, at?: string): Promise<WorkspaceNetWorth> =>
    api
      .get<WorkspaceNetWorth>(`/workspaces/${workspaceId}/net-worth`, { params: at ? { at } : {} })
      .then((r: AxiosResponse<WorkspaceNetWorth>) => r.data),

  getWorkspaceNetWorthTimeseries: (
    workspaceId: string,
    from: string,
    to: string,
    granularity = 'monthly',
  ): Promise<WorkspaceNetWorthTimeseries> =>
    api
      .get<WorkspaceNetWorthTimeseries>(`/workspaces/${workspaceId}/net-worth/timeseries`, {
        params: { from, to, granularity },
      })
      .then((r: AxiosResponse<WorkspaceNetWorthTimeseries>) => r.data),
}
