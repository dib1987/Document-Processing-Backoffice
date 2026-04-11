'use client'

import { useState } from 'react'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { api, setAuthHeaders } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Download, FileText, FileJson } from 'lucide-react'
import { useCurrentUser } from '@/lib/hooks/useCurrentUser'

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'crm_written', label: 'In HubSpot' },
  { value: 'review_queue', label: 'Needs Review' },
  { value: 'error', label: 'Error' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'reupload_requested', label: 'Re-upload Needed' },
]

function useSetupHeaders() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  return async () => {
    const token = await getToken()
    if (token && organization?.id) setAuthHeaders(token, organization.id)
  }
}

export default function ExportPage() {
  const { data: currentUser } = useCurrentUser()
  const setupHeaders = useSetupHeaders()
  const { toast } = useToast()

  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [includeAudit, setIncludeAudit] = useState(false)
  const [loadingCsv, setLoadingCsv] = useState(false)
  const [loadingJson, setLoadingJson] = useState(false)

  if (currentUser?.role !== 'admin') {
    return (
      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <p className="text-slate-500 text-sm">You do not have permission to access this page.</p>
        </div>
      </div>
    )
  }

  async function downloadFile(format: 'csv' | 'json') {
    const setter = format === 'csv' ? setLoadingCsv : setLoadingJson
    setter(true)
    try {
      await setupHeaders()

      const params: Record<string, string> = {}
      if (statusFilter) params.status_filter = statusFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (format === 'json' && includeAudit) params.include_audit = 'true'

      const res = await api.get(`/export/${format}`, {
        params,
        responseType: 'blob',
      })

      const disposition = res.headers['content-disposition'] as string | undefined
      let filename = `docflow_export.${format}`
      if (disposition) {
        const match = disposition.match(/filename="(.+)"/)
        if (match) filename = match[1]
      }

      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      toast({ title: `${format.toUpperCase()} export downloaded` })
    } catch {
      toast({ title: `Failed to download ${format.toUpperCase()}`, variant: 'destructive' })
    } finally {
      setter(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-1">Export Filters</h2>
        <p className="text-sm text-slate-400 mb-4">
          Narrow the export by status or date range. Leave blank to export all patient documents.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-300"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div />

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Date From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-300"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Date To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-300"
            />
          </div>
        </div>
      </div>

      {/* Download CSV */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-slate-800">CSV Export</h3>
            <p className="text-sm text-slate-400 mt-0.5">
              Document metadata and extracted patient fields in a spreadsheet-friendly format. Opens directly in Excel or Google Sheets.
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-500 list-disc list-inside">
              <li>Job ID, filename, document type, status</li>
              <li>Extracted fields (patient name, DOB, insurance ID, provider, etc.)</li>
              <li>HubSpot contact ID, processing time, upload date</li>
            </ul>
          </div>
          <button
            onClick={() => downloadFile('csv')}
            disabled={loadingCsv}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50 shrink-0"
          >
            <Download className="w-4 h-4" />
            {loadingCsv ? 'Downloading…' : 'Download CSV'}
          </button>
        </div>
      </div>

      {/* Download JSON */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-teal-50 rounded-lg flex items-center justify-center shrink-0">
            <FileJson className="w-5 h-5 text-teal-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-slate-800">JSON Export</h3>
            <p className="text-sm text-slate-400 mt-0.5">
              Full structured export including confidence scores, validation flags, and optionally the complete audit trail per document. Useful for compliance and integration.
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-500 list-disc list-inside">
              <li>All extracted fields + per-field confidence scores</li>
              <li>Validation flags and failure reasons</li>
              <li>Optional: full audit log per document</li>
            </ul>
            <label className="flex items-center gap-2 mt-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeAudit}
                onChange={(e) => setIncludeAudit(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-teal-600 focus:ring-teal-300"
              />
              <span className="text-xs font-medium text-slate-600">Include audit trail per document</span>
            </label>
          </div>
          <button
            onClick={() => downloadFile('json')}
            disabled={loadingJson}
            className="flex items-center gap-2 px-4 py-2 bg-teal-700 text-white text-sm font-medium rounded-lg hover:bg-teal-800 disabled:opacity-50 shrink-0"
          >
            <Download className="w-4 h-4" />
            {loadingJson ? 'Downloading…' : 'Download JSON'}
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <p className="text-xs text-slate-500 leading-relaxed">
          <strong className="text-slate-600">Data scope:</strong> Exports include only documents from your organisation.
          All sensitive identifiers are masked in the source data and will appear masked in the export.
          This page is visible to <strong className="text-slate-600">admin</strong> users only.
        </p>
      </div>
    </div>
  )
}
