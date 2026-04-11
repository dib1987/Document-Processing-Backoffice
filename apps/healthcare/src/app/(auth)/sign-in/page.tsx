import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center">
      {/* Background texture */}
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 flex flex-col items-center gap-8">
        {/* Logo / Brand */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="w-10 h-10 bg-indigo-500 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">DocFlow AI</span>
          </div>
          <p className="text-slate-400 text-sm">Document intelligence for accounting firms</p>
        </div>

        <SignIn
          appearance={{
            elements: {
              rootBox: 'shadow-2xl',
              card: 'rounded-xl border border-slate-700 bg-navy-800',
              headerTitle: 'text-white',
              headerSubtitle: 'text-slate-400',
              socialButtonsBlockButton: 'bg-navy-700 border-slate-600 text-white hover:bg-navy-600',
              dividerLine: 'bg-slate-700',
              dividerText: 'text-slate-400',
              formFieldLabel: 'text-slate-300',
              formFieldInput: 'bg-navy-700 border-slate-600 text-white placeholder-slate-500 focus:border-indigo-500',
              formButtonPrimary: 'bg-indigo-600 hover:bg-indigo-500',
              footerActionLink: 'text-indigo-400 hover:text-indigo-300',
            },
          }}
        />
      </div>
    </div>
  )
}
