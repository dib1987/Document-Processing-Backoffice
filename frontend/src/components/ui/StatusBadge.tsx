import { JobStatus } from '@/lib/api'
import { STATUS_CONFIG, isProcessing, cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: JobStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, color: 'text-slate-500', bg: 'bg-slate-100' }
  const spinning = isProcessing(status)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium',
        config.bg,
        config.color,
        className,
      )}
    >
      {spinning ? (
        <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <span className={cn('w-1.5 h-1.5 rounded-full bg-current')} />
      )}
      {config.label}
    </span>
  )
}
