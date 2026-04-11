'use client'

import { useQuery } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { auditApi, setAuthHeaders } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Shield } from 'lucide-react'
import { useCurrentUser } from '@/lib/hooks/useCurrentUser'

function useAuditLog() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  return useQuery({
    queryKey: ['audit-log'],
    queryFn: async () => {
      const token = await getToken()
      if (token && organization?.id) setAuthHeaders(token, organization.id)
      const res = await auditApi.list()
      return res.data
    },
    staleTime: 30_000,
  })
}

const ACTION_COLORS: Record<string, string> = {
  UPLOADED:          'bg-blue-50 text-blue-700',
  OCR_STARTED:       'bg-slate-50 text-slate-600',
  OCR_COMPLETE:      'bg-slate-50 text-slate-600',
  EXTRACTED:         'bg-purple-50 text-purple-700',
  FLAGGED:           'bg-amber-50 text-amber-700',
  REVIEWED:          'bg-sky-50 text-sky-700',
  FIELD_CHANGED:     'bg-sky-50 text-sky-700',
  APPROVED:          'bg-emerald-50 text-emerald-700',
  REJECTED:          'bg-red-50 text-red-700',
  CRM_WRITTEN:       'bg-indigo-50 text-indigo-700',
  CRM_ERROR:         'bg-red-50 text-red-700',
  REUPLOAD_REQUESTED:'bg-amber-50 text-amber-700',
  ERROR:             'bg-red-50 text-red-700',
}

export default function AuditPage() {
  const { data: currentUser } = useCurrentUser()
  const { data: entries, isLoading } = useAuditLog()

  if (currentUser && currentUser.role === 'viewer') {
    return (
      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <p className="text-slate-500 text-sm">You do not have permission to access this page.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200">
      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="font-semibold text-slate-800">Audit Trail</h2>
        <p className="text-sm text-slate-400 mt-0.5">All document processing actions</p>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />)}
        </div>
      ) : !entries?.length ? (
        <div className="p-16 text-center">
          <Shield className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 font-medium">No audit entries yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Time</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Actor</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Action</th>
                <th className="text-left px-5 py-3 text-slate-500 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry: any) => (
                <tr key={entry.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-slate-400 whitespace-nowrap">{formatDate(entry.created_at)}</td>
                  <td className="px-5 py-3 text-slate-600 font-medium">{entry.actor}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_COLORS[entry.action] ?? 'bg-slate-100 text-slate-600'}`}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-400 text-xs max-w-xs truncate">
                    {entry.detail ? JSON.stringify(entry.detail) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
