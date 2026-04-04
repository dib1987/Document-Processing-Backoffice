import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@clerk/nextjs'
import { authApi, setAuthHeaders } from '@/lib/api'
import { useOrganization } from '@clerk/nextjs'

export function useCurrentUser() {
  const { getToken, userId } = useAuth()
  const { organization } = useOrganization()

  return useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const token = await getToken()
      const orgId = organization?.id ?? userId ?? ''
      if (token) setAuthHeaders(token, orgId)
      const res = await authApi.me()
      return res.data
    },
    staleTime: 60_000,
  })
}
