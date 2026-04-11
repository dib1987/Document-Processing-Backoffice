import { useQuery } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { dashboardApi, setAuthHeaders } from '@/lib/api'

export function useDashboard() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()

  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const token = await getToken()
      if (token && organization?.id) {
        setAuthHeaders(token, organization.id)
      }
      const res = await dashboardApi.stats()
      return res.data
    },
    refetchInterval: 30_000, // refresh every 30s
    staleTime: 20_000,
  })
}
