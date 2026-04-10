'use client'

import { useState, useRef } from 'react'
import { useUpload, useJobStatus } from '@/lib/hooks/useJobs'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useToast } from '@/components/ui/use-toast'
import { Upload, FileText, X, CheckCircle } from 'lucide-react'
import { DocType } from '@/lib/api'
import { DOC_TYPE_LABELS } from '@/lib/utils'

const DOC_TYPES: DocType[] = ['tax_return', 'government_id', 'bank_statement', 'general']

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState<DocType>('tax_return')
  const [jobId, setJobId] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  const upload = useUpload()
  const { data: jobStatus } = useJobStatus(jobId)

  const handleFile = (f: File) => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase()
    if (ext !== '.pdf') {
      toast({ title: 'Unsupported file type. Please upload a PDF.', variant: 'destructive' })
      return
    }
    setFile(f)
    setJobId(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const handleSubmit = async () => {
    if (!file) return
    try {
      const result = await upload.mutateAsync({ file, docType })
      setJobId(result.job_id)
      setFile(null)
      toast({ title: 'Document uploaded — processing started' })
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? 'Unknown error'
      toast({ title: `Upload failed: ${msg}`, variant: 'destructive' })
    }
  }

  const isTerminal = jobStatus && ['crm_written', 'review_queue', 'error', 'crm_error', 'reupload_requested'].includes(jobStatus.status)

  const ACCEPT = '.pdf'

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50'
        }`}
      >
        <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
        <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
        <p className="font-medium text-slate-700">Drop a file here or click to browse</p>
        <p className="text-sm text-slate-400 mt-1">PDF only — maximum 50 MB</p>
      </div>

      {/* Selected file */}
      {file && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
          <FileText className="w-8 h-8 text-indigo-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-slate-800 truncate">{file.name}</p>
            <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
          <button onClick={() => setFile(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Doc type selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <label className="block text-sm font-medium text-slate-700 mb-3">Document Type</label>
        <div className="grid grid-cols-2 gap-2">
          {DOC_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => setDocType(type)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                docType === type
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
              }`}
            >
              {DOC_TYPE_LABELS[type]}
            </button>
          ))}
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || upload.isPending}
        className="w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {upload.isPending ? 'Uploading...' : 'Upload & Process'}
      </button>

      {/* Job status tracker — shown as soon as jobId exists, even before first poll */}
      {jobId && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-slate-800">Processing Status</h3>
            {!isTerminal && (
              jobStatus
                ? <StatusBadge status={jobStatus.status} />
                : <span className="text-xs font-medium px-2 py-1 rounded-full bg-slate-100 text-slate-500">queued</span>
            )}
          </div>
          {isTerminal && !['error', 'crm_error'].includes(jobStatus?.status ?? '') && (
            <div className="flex items-center gap-2 text-emerald-600 text-sm mt-2">
              <CheckCircle className="w-4 h-4" />
              <span>Upload successful — you will be notified by email.</span>
            </div>
          )}
          {isTerminal && ['error', 'crm_error'].includes(jobStatus?.status ?? '') && (
            <p className="text-red-600 text-sm mt-2">Processing failed. Please try again or contact support.</p>
          )}
          {!isTerminal && (
            <div className="flex items-center gap-2 text-blue-600 text-sm mt-2">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span>{jobStatus ? 'Processing your document...' : 'Queued — waiting for worker...'}</span>
            </div>
          )}
          {isTerminal && (
            <button
              onClick={() => { setJobId(null); setFile(null) }}
              className="mt-4 w-full py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              Upload Another Document
            </button>
          )}
        </div>
      )}
    </div>
  )
}
