import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Injected at call sites with getToken() from useAuth
export function setAuthHeaders(token: string, orgId: string) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  api.defaults.headers.common['x-org-id'] = orgId
}

// ── Types ──────────────────────────────────────────────────

export type JobStatus =
  | 'pending' | 'queued' | 'ocr' | 'extracting' | 'validating'
  | 'review_queue' | 'crm_pending' | 'crm_written' | 'crm_error' | 'error'

export type DocType = 'tax_return' | 'government_id' | 'bank_statement' | 'general'

export interface Job {
  job_id: string
  original_filename: string
  doc_type: DocType
  status: JobStatus
  page_count: number | null
  crm_contact_id: string | null
  processing_ms: number | null
  error_message: string | null
  created_at: string
  updated_at: string | null
}

export interface JobDetail extends Job {
  presigned_url: string | null
  extraction: {
    fields: Record<string, string | null>
    confidence: Record<string, string>
  } | null
  flags: Array<{
    flag_type: string
    field_name: string
    plain_message: string
  }>
}

export interface ReviewItem {
  review_id: string
  job_id: string
  filename: string
  doc_type: DocType
  flag_count: number
  flags: string[]
  created_at: string
}

export interface DashboardStats {
  stats: {
    docs_processed_this_month: number
    hours_saved_this_month: number
    auto_approved_rate: number
    pending_review_count: number
  }
  weekly_chart: Array<{ week_label: string; count: number }>
  recent_jobs: Array<{
    job_id: string
    filename: string
    doc_type: DocType
    status: JobStatus
    processing_ms: number | null
    created_at: string
  }>
}

export interface AuditEntry {
  id: string
  job_id: string | null
  user_id: string | null
  actor: string | null
  action: string
  detail: Record<string, unknown> | null
  created_at: string
}

// ── API Functions ──────────────────────────────────────────

export const jobsApi = {
  upload: (file: File, docType: DocType) => {
    const form = new FormData()
    form.append('file', file)
    form.append('doc_type', docType)
    return api.post<{ job_id: string; status: string }>('/jobs/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: (params?: { status_filter?: string; limit?: number; offset?: number }) =>
    api.get<Job[]>('/jobs', { params }),
  status: (jobId: string) =>
    api.get<{ job_id: string; status: JobStatus; error_message: string | null }>(`/jobs/${jobId}/status`),
  detail: (jobId: string) => api.get<JobDetail>(`/jobs/${jobId}`),
}

export const reviewApi = {
  list: () => api.get<ReviewItem[]>('/review'),
  detail: (jobId: string) => api.get<JobDetail>('/review/' + jobId),
  approve: (jobId: string, correctedFields: Record<string, string>) =>
    api.post(`/review/${jobId}/approve`, { corrected_fields: correctedFields }),
  reject: (jobId: string, reason: string) =>
    api.post(`/review/${jobId}/reject`, { reason }),
}

export const dashboardApi = {
  stats: () => api.get<DashboardStats>('/dashboard/stats'),
}

export const auditApi = {
  list: (params?: {
    job_id?: string
    user_id?: string
    action?: string
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  }) => api.get<AuditEntry[]>('/audit', { params }),
}

export const settingsApi = {
  getHubspot: () => api.get<{ connected: boolean; masked_key: string | null }>('/settings/hubspot'),
  saveHubspot: (apiKey: string) => api.put('/settings/hubspot', { api_key: apiKey }),
  getAllMappings: () => api.get<Record<string, { mapping: Record<string, string>; updated_at: string | null }>>('/settings/field-mapping/all'),
  saveMapping: (docType: string, mapping: Record<string, string>) =>
    api.put('/settings/field-mapping', { doc_type: docType, mapping }),
  resetMapping: (docType: string) =>
    api.post(`/settings/field-mapping/reset?doc_type=${docType}`),
}

export const exportApi = {
  csv: (params?: { status_filter?: string; date_from?: string; date_to?: string }) =>
    api.get('/export/csv', { params, responseType: 'blob' }),
  json: (params?: { status_filter?: string; date_from?: string; date_to?: string; include_audit?: boolean }) =>
    api.get('/export/json', { params, responseType: 'blob' }),
}
