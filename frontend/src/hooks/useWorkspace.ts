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
