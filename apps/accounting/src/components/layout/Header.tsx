'use client'

import { useOrganization, UserButton } from '@clerk/nextjs'
import { Menu, Bell } from 'lucide-react'
import { useReviewQueue } from '@/lib/hooks/useReviewQueue'
import Link from 'next/link'

interface HeaderProps {
  onMenuClick: () => void
  title: string
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { organization } = useOrganization()
  const { data: reviewItems } = useReviewQueue()
  const pendingCount = reviewItems?.length ?? 0

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-6 shrink-0">
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Page title */}
        <h1 className="font-semibold text-slate-800 text-lg">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Org name */}
        {organization && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
            <div className="w-2 h-2 bg-emerald-500 rounded-full" />
            <span className="text-sm font-medium text-slate-700 max-w-[180px] truncate">
              {organization.name}
            </span>
          </div>
        )}

        {/* Review queue notification */}
        {pendingCount > 0 && (
          <Link
            href="/review"
            className="relative p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          >
            <Bell className="w-5 h-5" />
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-amber-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          </Link>
        )}

        {/* User avatar */}
        <UserButton
          afterSignOutUrl="/sign-in"
          appearance={{
            elements: {
              avatarBox: 'w-8 h-8 rounded-lg',
            },
          }}
        />
      </div>
    </header>
  )
}
