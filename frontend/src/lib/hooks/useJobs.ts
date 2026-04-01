import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { jobsApi, setAuthHeaders, DocType } from '@/lib/api'

function useAuthHeaders() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  return async () => {
    const token = await getToken()
    if (token && organization?.id) setAuthHeaders(token, organization.id)
  }
}

export function useJobs(params?: { status_filter?: string; limit?: number }) {
  const setupHeaders = useAuthHeaders()
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: async () => {
      await setupHeaders()
      const res = await jobsApi.list(params)
      return res.data
    },
    staleTime: 10_000,
  })
}

export function useJobStatus(jobId: string | null, enabled = true) {
  const setupHeaders = useAuthHeaders()
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: async () => {
      await setupHeaders()
      const res = await jobsApi.status(jobId!)
      return res.data
    },
    enabled: !!jobId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      const done = status === 'crm_written' || status === 'review_queue' || status === 'error' || status === 'crm_error'
      return done ? false : 3_000
    },
  })
}

export function useJobDetail(jobId: string | null) {
  const setupHeaders = useAuthHeaders()
  return useQuery({
    queryKey: ['job-detail', jobId],
    queryFn: async () => {
      await setupHeaders()
      const res = await jobsApi.detail(jobId!)
      return res.data
    },
    enabled: !!jobId,
  })
}

export function useUpload() {
  const setupHeaders = useAuthHeaders()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ file, docType }: { file: File; docType: DocType }) => {
      await setupHeaders()
      const res = await jobsApi.upload(file, docType)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}
