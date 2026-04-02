'use client'

import { useJobs } from '@/lib/hooks/useJobs'
import { useDashboard } from '@/lib/hooks/useDashboard'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDate, DOC_TYPE_LABELS } from '@/lib/utils'
import { FileText, CheckCircle, Clock, AlertTriangle, TrendingUp } from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboard()
  const { data: jobs, isLoading: jobsLoading } = useJobs({ limit: 10 })

  const statCards = [
    {
      label: 'Total Processed',
      value: stats?.total_processed ?? 0,
      icon: FileText,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
    {
      label: 'Auto-Approved',
      value: stats?.auto_approved ?? 0,
      icon: CheckCircle,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      label: 'Pending Review',
      value: stats?.pending_review ?? 0,
      icon: Clock,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
    {
      label: 'Errors',
      value: stats?.errors ?? 0,
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-slate-500 font-medium">{label}</span>
              <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
            </div>
            {statsLoading ? (
              <div className="h-8 w-16 bg-slate-100 rounded animate-pulse" />
            ) : (
              <p className="text-3xl font-bold text-slate-800">{value}</p>
            )}
          </div>
        ))}
      </div>

      {/* Hours saved */}
      {stats && (
        <div className="bg-gradient-to-r from-indigo-600 to-indigo-500 rounded-xl p-5 text-white flex items-center justify-between">
          <div>
            <p className="text-indigo-200 text-sm font-medium">Estimated Time Saved</p>
            <p className="text-3xl font-bold mt-1">{stats.hours_saved?.toFixed(1) ?? '0'} hrs</p>
            <p className="text-indigo-200 text-sm mt-1">Based on {stats.total_processed} documents processed</p>
          </div>
          <TrendingUp className="w-12 h-12 text-indigo-300 opacity-80" />
        </div>
      )}

      {/* Recent Jobs */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">Recent Documents</h2>
          <Link href="/upload" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
            + Upload New
          </Link>
        </div>

        {jobsLoading ? (
          <div className="p-5 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : !jobs?.length ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500 font-medium">No documents yet</p>
            <p className="text-slate-400 text-sm mt-1">Upload your first document to get started</p>
            <Link
              href="/upload"
              className="mt-4 inline-block px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
            >
              Upload Document
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-slate-500 font-medium">File</th>
                  <th className="text-left px-5 py-3 text-slate-500 font-medium">Type</th>
                  <th className="text-left px-5 py-3 text-slate-500 font-medium">Status</th>
                  <th className="text-left px-5 py-3 text-slate-500 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-slate-800 max-w-[200px] truncate">
                      {job.original_filename}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {DOC_TYPE_LABELS[job.doc_type] ?? job.doc_type}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">
                      {formatDate(job.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
