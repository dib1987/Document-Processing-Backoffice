import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { reviewApi, setAuthHeaders } from '@/lib/api'

function useAuthHeaders() {
  const { getToken, userId } = useAuth()
  const { organization } = useOrganization()
  return async () => {
    const token = await getToken()
    const orgId = organization?.id ?? userId ?? ''
    if (token) setAuthHeaders(token, orgId)
  }
}

export function useReviewQueue() {
  const setupHeaders = useAuthHeaders()
  return useQuery({
    queryKey: ['review-queue'],
    queryFn: async () => {
      await setupHeaders()
      const res = await reviewApi.list()
      return res.data
    },
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

export function useReviewDetail(jobId: string | null) {
  const setupHeaders = useAuthHeaders()
  return useQuery({
    queryKey: ['review-detail', jobId],
    queryFn: async () => {
      await setupHeaders()
      const res = await reviewApi.detail(jobId!)
      return res.data
    },
    enabled: !!jobId,
  })
}

export function useApprove() {
  const setupHeaders = useAuthHeaders()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ jobId, correctedFields }: { jobId: string; correctedFields: Record<string, string> }) => {
      await setupHeaders()
      return reviewApi.approve(jobId, correctedFields)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}

export function useReject() {
  const setupHeaders = useAuthHeaders()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ jobId, reason }: { jobId: string; reason: string }) => {
      await setupHeaders()
      return reviewApi.reject(jobId, reason)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}
