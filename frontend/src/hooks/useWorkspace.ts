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
    mutationFn: (email: string) => workspaceApi.invite(workspaceId, email),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspace-members', workspaceId] })
      qc.invalidateQueries({ queryKey: ['me'] })
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
