'use client'

import { useState } from 'react'
import { useReviewQueue, useReviewDetail, useApprove, useReject, useRequestReupload } from '@/lib/hooks/useReviewQueue'
import { useToast } from '@/components/ui/use-toast'
import { formatDate, DOC_TYPE_LABELS } from '@/lib/utils'
import { ClipboardList, CheckCircle, XCircle, ChevronRight, X, Mail } from 'lucide-react'

export default function ReviewQueuePage() {
  const { data: items, isLoading } = useReviewQueue()
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)
  const [showReupload, setShowReupload] = useState(false)
  const [reuploadMessage, setReuploadMessage] = useState('')
  const [editedFields, setEditedFields] = useState<Record<string, string>>({})
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const { toast } = useToast()

  const { data: detail } = useReviewDetail(selectedJobId)
  const approve = useApprove()
  const reject = useReject()
  const requestReupload = useRequestReupload()

  const handleApprove = async () => {
    if (!selectedJobId) return
    try {
      const mergedFields = { ...detail?.fields ?? {}, ...editedFields }
      await approve.mutateAsync({ jobId: selectedJobId, correctedFields: mergedFields })
      toast({ title: 'Document approved and pushed to HubSpot' })
      setSelectedJobId(null)
      setEditedFields({})
    } catch {
      toast({ title: 'Approval failed', variant: 'destructive' })
    }
  }

  const handleReject = async () => {
    if (!selectedJobId) return
    try {
      await reject.mutateAsync({ jobId: selectedJobId, reason: rejectReason })
      toast({ title: 'Document rejected' })
      setSelectedJobId(null)
      setRejectReason('')
      setShowReject(false)
    } catch {
      toast({ title: 'Rejection failed', variant: 'destructive' })
    }
  }

  const handleRequestReupload = async () => {
    if (!selectedJobId) return
    try {
      const res = await requestReupload.mutateAsync({ jobId: selectedJobId, message: reuploadMessage })
      const notified = res.data.notified
      toast({
        title: 'Re-upload request sent',
        description: notified ? `Email sent to ${notified}` : 'Request logged (email not configured)',
      })
      setSelectedJobId(null)
      setReuploadMessage('')
      setShowReupload(false)
    } catch {
      toast({ title: 'Failed to send re-upload request', variant: 'destructive' })
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-white rounded-xl border border-slate-200 animate-pulse" />)}
      </div>
    )
  }

  if (!items?.length) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-16 text-center">
        <ClipboardList className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <p className="font-semibold text-slate-600">Review queue is empty</p>
        <p className="text-slate-400 text-sm mt-1">All documents have been processed</p>
      </div>
    )
  }

  return (
    <div className="flex gap-6 h-full">
      {/* List */}
      <div className="w-full lg:w-96 space-y-2 shrink-0">
        {items.map((item) => (
          <button
            key={item.job_id}
            onClick={() => setSelectedJobId(item.job_id)}
            className={`w-full text-left bg-white rounded-xl border p-4 transition-colors hover:border-indigo-300 ${
              selectedJobId === item.job_id ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="font-medium text-slate-800 truncate max-w-[200px]">{item.filename}</p>
              <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
            </div>
            <p className="text-sm text-slate-400 mt-1">{DOC_TYPE_LABELS[item.doc_type]}</p>
            <p className="text-xs text-slate-400 mt-1">{formatDate(item.created_at)}</p>
            {item.flag_count > 0 && (
              <span className="mt-2 inline-block px-2 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full">
                {item.flag_count} validation {item.flag_count === 1 ? 'issue' : 'issues'}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Detail panel */}
      {selectedJobId && detail ? (
        <div className="flex-1 bg-white rounded-xl border border-slate-200 p-5 overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-800 truncate">{detail.filename}</h2>
            <button onClick={() => setSelectedJobId(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Validation flags */}
          {detail.flags && detail.flags.length > 0 && (
            <div className="mb-4 space-y-2">
              <h3 className="text-sm font-medium text-slate-600">Validation Issues</h3>
              {detail.flags.map((flag: any) => (
                <div key={flag.id} className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-100 rounded-lg">
                  <span className="text-amber-500 text-sm">⚠</span>
                  <p className="text-sm text-amber-700">{flag.plain_message}</p>
                </div>
              ))}
            </div>
          )}

          {/* Extracted fields */}
          {detail.fields && Object.keys(detail.fields).length > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-slate-600">Extracted Fields</h3>
                <span className="text-xs text-slate-400">Click a value to edit</span>
              </div>
              <div className="space-y-1">
                {Object.entries(detail.fields).map(([key, value]) => {
                  const displayValue = editedFields[key] ?? String(value ?? '')
                  const isEdited = key in editedFields
                  const isEditing = editingKey === key
                  return (
                    <div key={key} className="flex items-center justify-between py-2 border-b border-slate-50 gap-4">
                      <span className="text-sm text-slate-500 capitalize shrink-0">{key.replace(/_/g, ' ')}</span>
                      {isEditing ? (
                        <input
                          autoFocus
                          className="text-sm font-medium text-slate-800 text-right border border-indigo-300 rounded px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-indigo-400 w-48"
                          value={displayValue}
                          onChange={(e) => setEditedFields(prev => ({ ...prev, [key]: e.target.value }))}
                          onBlur={() => setEditingKey(null)}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === 'Escape') setEditingKey(null) }}
                        />
                      ) : (
                        <button
                          onClick={() => {
                            if (!(key in editedFields)) setEditedFields(prev => ({ ...prev, [key]: String(value ?? '') }))
                            setEditingKey(key)
                          }}
                          className={`text-sm font-medium text-right px-2 py-0.5 rounded hover:bg-indigo-50 hover:text-indigo-700 transition-colors ${isEdited ? 'text-indigo-600' : 'text-slate-800'}`}
                          title="Click to edit"
                        >
                          {displayValue || <span className="text-slate-300 italic">empty</span>}
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
              {Object.keys(editedFields).length > 0 && (
                <p className="text-xs text-indigo-500 mt-2">{Object.keys(editedFields).length} field(s) edited</p>
              )}
            </div>
          )}

          {/* Actions */}
          {!showReject && !showReupload ? (
            <div className="space-y-2">
              <button
                onClick={() => setShowReupload(true)}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700"
              >
                <Mail className="w-4 h-4" />
                Request Re-upload
              </button>
              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={approve.isPending}
                  className="flex-1 flex items-center justify-center gap-2 py-2 bg-emerald-50 text-emerald-700 font-medium rounded-lg hover:bg-emerald-100 border border-emerald-200 disabled:opacity-50 text-sm"
                >
                  <CheckCircle className="w-4 h-4" />
                  {approve.isPending ? 'Approving...' : 'Approve & Push to CRM'}
                </button>
                <button
                  onClick={() => setShowReject(true)}
                  className="flex-1 flex items-center justify-center gap-2 py-2 bg-red-50 text-red-600 font-medium rounded-lg hover:bg-red-100 border border-red-200 text-sm"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            </div>
          ) : showReupload ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-500">An email will be sent to the document uploader asking them to re-upload with corrections.</p>
              <textarea
                value={reuploadMessage}
                onChange={(e) => setReuploadMessage(e.target.value)}
                placeholder="Optional message to the uploader (e.g. 'Please ensure the SSN is clearly visible')"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none h-24 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleRequestReupload}
                  disabled={requestReupload.isPending}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Mail className="w-4 h-4" />
                  {requestReupload.isPending ? 'Sending...' : 'Send Re-upload Request'}
                </button>
                <button
                  onClick={() => { setShowReupload(false); setReuploadMessage('') }}
                  className="px-4 py-2.5 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Reason for rejection (optional)"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none h-24 focus:outline-none focus:ring-2 focus:ring-red-300"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleReject}
                  disabled={reject.isPending}
                  className="flex-1 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {reject.isPending ? 'Rejecting...' : 'Confirm Reject'}
                </button>
                <button
                  onClick={() => setShowReject(false)}
                  className="px-4 py-2.5 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 hidden lg:flex items-center justify-center bg-white rounded-xl border border-slate-200 border-dashed">
          <p className="text-slate-400">Select a document to review</p>
        </div>
      )}
    </div>
  )
}
