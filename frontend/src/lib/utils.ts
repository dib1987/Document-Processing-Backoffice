import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { JobStatus, DocType } from './api'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMs(ms: number | null): string {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s % 60)
  return `${m}m ${rem}s`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateShort(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  tax_return: 'Tax Return',
  government_id: 'Government ID',
  bank_statement: 'Bank Statement',
  general: 'General Document',
}

export const STATUS_CONFIG: Record<JobStatus, { label: string; color: string; bg: string }> = {
  pending:      { label: 'Pending',     color: 'text-slate-500', bg: 'bg-slate-100' },
  queued:       { label: 'Queued',      color: 'text-blue-700',  bg: 'bg-blue-50' },
  ocr:          { label: 'Analyzing',   color: 'text-blue-700',  bg: 'bg-blue-50' },
  extracting:   { label: 'Extracting',  color: 'text-blue-700',  bg: 'bg-blue-50' },
  validating:   { label: 'Validating',  color: 'text-blue-700',  bg: 'bg-blue-50' },
  review_queue: { label: 'Needs Review',color: 'text-amber-700', bg: 'bg-amber-50' },
  crm_pending:  { label: 'Sending...',  color: 'text-indigo-700',bg: 'bg-indigo-50' },
  crm_written:  { label: 'In HubSpot',  color: 'text-emerald-700', bg: 'bg-emerald-50' },
  crm_error:    { label: 'CRM Error',   color: 'text-red-700',   bg: 'bg-red-50' },
  error:        { label: 'Error',       color: 'text-red-700',   bg: 'bg-red-50' },
}

export function isProcessing(status: JobStatus): boolean {
  return ['queued', 'ocr', 'extracting', 'validating', 'crm_pending'].includes(status)
}

export const CONFIDENCE_CONFIG = {
  high:      { label: 'Confident',                  color: 'text-emerald-700', dot: 'bg-emerald-500' },
  medium:    { label: 'Uncertain — please verify',  color: 'text-amber-700',   dot: 'bg-amber-500' },
  low:       { label: 'Could not read — enter manually', color: 'text-red-700', dot: 'bg-red-500' },
  not_found: { label: 'Could not read — enter manually', color: 'text-red-700', dot: 'bg-red-500' },
}
