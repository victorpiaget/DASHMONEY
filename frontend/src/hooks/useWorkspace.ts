import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { workspaceApi } from '../lib/workspaceApi'

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: workspaceApi.me,
    staleTime: 60_000,
  })
}

export function useWorkspaceMembers(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['workspace-members', workspaceId],
    queryFn: () => workspaceApi.listMembers(workspaceId!),
    enabled: !!workspaceId,
  })
}

export function useInviteMember(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: 'OWNER' | 'MEMBER' | 'READ_ONLY' }) =>
      workspaceApi.invite(workspaceId, email, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-members', workspaceId] })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useCreateWorkspace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => workspaceApi.createWorkspace(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useUpdateMemberRole(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'OWNER' | 'MEMBER' | 'READ_ONLY' }) =>
      workspaceApi.updateMemberRole(workspaceId, userId, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-members', workspaceId] })
    },
  })
}

export function useRemoveMember(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => workspaceApi.removeMember(workspaceId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-members', workspaceId] })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}

export function useRenameWorkspace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workspaceId, name }: { workspaceId: string; name: string }) =>
      workspaceApi.renameWorkspace(workspaceId, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useCreateProfile(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (displayName: string) => workspaceApi.createProfile(workspaceId, displayName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useRenameProfile(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ profileId, displayName }: { profileId: string; displayName: string }) =>
      workspaceApi.renameProfile(workspaceId, profileId, displayName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useDeleteProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (profileId: string) => workspaceApi.deleteProfile(profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useLinkProfile(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (profileId: string) => workspaceApi.linkProfile(workspaceId, profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useUnlinkProfile(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (profileId: string) => workspaceApi.unlinkProfile(workspaceId, profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useWorkspaceNetWorth(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['workspace-nw', workspaceId],
    queryFn: () => workspaceApi.getWorkspaceNetWorth(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 60_000,
  })
}

export function useWorkspaceNetWorthTimeseries(
  workspaceId: string | undefined,
  from: string,
  to: string,
  granularity = 'monthly',
) {
  return useQuery({
    queryKey: ['workspace-nw-ts', workspaceId, from, to, granularity],
    queryFn: () => workspaceApi.getWorkspaceNetWorthTimeseries(workspaceId!, from, to, granularity),
    enabled: !!workspaceId,
    staleTime: 60_000,
  })
}
