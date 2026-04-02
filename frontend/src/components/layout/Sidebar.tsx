'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Upload, ClipboardList, Shield, Settings, FileText, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReviewQueue } from '@/lib/hooks/useReviewQueue'

interface SidebarProps {
  onClose?: () => void
}

const navItems = [
  { href: '/dashboard', label: 'Dashboard',    icon: LayoutDashboard },
  { href: '/upload',    label: 'Upload',       icon: Upload },
  { href: '/review',    label: 'Review Queue', icon: ClipboardList, showBadge: true },
  { href: '/audit',     label: 'Audit Trail',  icon: Shield },
  { href: '/settings',  label: 'Settings',     icon: Settings },
]

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()
  const { data: reviewItems } = useReviewQueue()
  const pendingCount = reviewItems?.length ?? 0

  return (
    <aside className="flex flex-col h-full bg-navy-900 w-64 shrink-0">
      {/* Logo */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-navy-700">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-white text-lg tracking-tight">DocFlow AI</span>
        </Link>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-white lg:hidden">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon, showBadge }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/50'
                  : 'text-slate-400 hover:text-white hover:bg-navy-800',
              )}
            >
              <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-white' : 'text-slate-500')} />
              <span className="flex-1">{label}</span>
              {showBadge && pendingCount > 0 && (
                <span className={cn(
                  'px-1.5 py-0.5 rounded-full text-xs font-semibold min-w-[20px] text-center',
                  isActive ? 'bg-white/20 text-white' : 'bg-amber-500 text-white',
                )}>
                  {pendingCount}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-navy-700">
        <p className="text-xs text-slate-600 leading-tight">
          AI-powered document processing.<br />
          Trusted by accounting professionals.
        </p>
      </div>
    </aside>
  )
}
