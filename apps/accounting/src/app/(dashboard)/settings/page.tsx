'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { settingsApi, setAuthHeaders, DocType } from '@/lib/api'
import { DOC_TYPE_LABELS } from '@/lib/utils'
import { useToast } from '@/components/ui/use-toast'
import { Save, Eye, EyeOff, RotateCcw } from 'lucide-react'
import { useCurrentUser } from '@/lib/hooks/useCurrentUser'

const ACCOUNTING_DOC_TYPES: DocType[] = [
  'tax_return',
  'government_id',
  'bank_statement',
  'general',
]

function useSetupHeaders() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  return async () => {
    const token = await getToken()
    if (token && organization?.id) setAuthHeaders(token, organization.id)
  }
}

function useHubspotSettings() {
  const setupHeaders = useSetupHeaders()
  return useQuery({
    queryKey: ['hubspot-settings'],
    queryFn: async () => {
      await setupHeaders()
      const res = await settingsApi.getHubspot()
      return res.data
    },
  })
}

function useAllMappings() {
  const setupHeaders = useSetupHeaders()
  return useQuery({
    queryKey: ['field-mappings'],
    queryFn: async () => {
      await setupHeaders()
      const res = await settingsApi.getAllMappings()
      return res.data
    },
  })
}

export default function SettingsPage() {
  const { data: currentUser } = useCurrentUser()
  const { data: hubspot } = useHubspotSettings()
  const { data: allMappings, isLoading: mappingsLoading } = useAllMappings()
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [activeDocType, setActiveDocType] = useState<DocType>('tax_return')

  if (currentUser && currentUser.role === 'viewer') {
    return (
      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <p className="text-slate-500 text-sm">You do not have permission to access this page.</p>
        </div>
      </div>
    )
  }
  // Local edits per doc type: { doc_type: { field: hubspotProp } }
  const [localMappings, setLocalMappings] = useState<Record<string, Record<string, string>>>({})
  const { toast } = useToast()
  const setupHeaders = useSetupHeaders()
  const queryClient = useQueryClient()

  // Initialise local state when server data arrives
  useEffect(() => {
    if (!allMappings) return
    const init: Record<string, Record<string, string>> = {}
    for (const dt of ACCOUNTING_DOC_TYPES) {
      if (allMappings[dt]) init[dt] = { ...allMappings[dt].mapping }
    }
    setLocalMappings(init)
  }, [allMappings])

  const saveHubspot = useMutation({
    mutationFn: async (key: string) => {
      await setupHeaders()
      return settingsApi.saveHubspot(key)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hubspot-settings'] })
      toast({ title: 'HubSpot API key saved' })
      setApiKey('')
    },
    onError: () => toast({ title: 'Failed to save', variant: 'destructive' }),
  })

  const saveMapping = useMutation({
    mutationFn: async ({ docType, mapping }: { docType: string; mapping: Record<string, string> }) => {
      await setupHeaders()
      return settingsApi.saveMapping(docType, mapping)
    },
    onSuccess: (_, { docType }) => {
      queryClient.invalidateQueries({ queryKey: ['field-mappings'] })
      toast({ title: `Mapping saved for ${DOC_TYPE_LABELS[docType as DocType] ?? docType}` })
    },
    onError: () => toast({ title: 'Failed to save mapping', variant: 'destructive' }),
  })

  const resetMapping = useMutation({
    mutationFn: async (docType: string) => {
      await setupHeaders()
      return settingsApi.resetMapping(docType)
    },
    onSuccess: (_, docType) => {
      queryClient.invalidateQueries({ queryKey: ['field-mappings'] })
      toast({ title: `Mapping reset to default for ${DOC_TYPE_LABELS[docType as DocType] ?? docType}` })
    },
    onError: () => toast({ title: 'Failed to reset mapping', variant: 'destructive' }),
  })

  const currentMapping = localMappings[activeDocType] ?? {}
  const serverUpdatedAt = allMappings?.[activeDocType]?.updated_at

  function setField(field: string, value: string) {
    setLocalMappings(prev => ({
      ...prev,
      [activeDocType]: { ...prev[activeDocType], [field]: value },
    }))
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* HubSpot Integration */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-1">HubSpot Integration</h2>
        <p className="text-sm text-slate-400 mb-4">
          Connect your HubSpot account to automatically push processed documents to your CRM.
        </p>

        {hubspot?.connected && (
          <div className="flex items-center gap-2 mb-4 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
            <div className="w-2 h-2 bg-emerald-500 rounded-full" />
            <span className="text-sm text-emerald-700 font-medium">HubSpot is connected</span>
            {hubspot.masked_key && (
              <span className="ml-auto text-xs text-slate-400 font-mono">{hubspot.masked_key}</span>
            )}
          </div>
        )}

        <label className="block text-sm font-medium text-slate-700 mb-2">
          {hubspot?.connected ? 'Update API Key' : 'HubSpot Private App API Key'}
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full px-3 py-2.5 pr-10 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <button
            onClick={() => apiKey && saveHubspot.mutate(apiKey)}
            disabled={!apiKey || saveHubspot.isPending}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saveHubspot.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Create a Private App in HubSpot → Settings → Integrations → Private Apps
        </p>
      </div>

      {/* Field Mapping */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-1">HubSpot Field Mapping</h2>
        <p className="text-sm text-slate-400 mb-4">
          Map extracted document fields to HubSpot contact properties. Use{' '}
          <code className="bg-slate-100 px-1 rounded text-xs">__split_name__</code> to split a full
          name into HubSpot <em>firstname</em> + <em>lastname</em>.
        </p>

        {/* Doc type tabs */}
        <div className="flex gap-1 mb-4 p-1 bg-slate-100 rounded-lg">
          {ACCOUNTING_DOC_TYPES.map((dt) => (
            <button
              key={dt}
              onClick={() => setActiveDocType(dt)}
              className={`flex-1 py-1.5 px-2 text-xs font-medium rounded-md transition-colors ${
                activeDocType === dt
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {DOC_TYPE_LABELS[dt]}
            </button>
          ))}
        </div>

        {mappingsLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-9 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            {serverUpdatedAt && (
              <p className="text-xs text-slate-400 mb-3">
                Last saved: {new Date(serverUpdatedAt).toLocaleString()}
              </p>
            )}

            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium w-1/2">
                      Extracted Field
                    </th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium w-1/2">
                      HubSpot Property
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(currentMapping).map(([field, hubspotProp], i) => (
                    <tr key={field} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                      <td className="px-4 py-2 font-mono text-xs text-slate-600">{field}</td>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={hubspotProp}
                          onChange={(e) => setField(field, e.target.value)}
                          className="w-full px-2 py-1 border border-slate-200 rounded text-xs focus:outline-none focus:ring-2 focus:ring-indigo-300"
                          placeholder="hubspot_property_name"
                        />
                      </td>
                    </tr>
                  ))}
                  {Object.keys(currentMapping).length === 0 && (
                    <tr>
                      <td colSpan={2} className="px-4 py-6 text-center text-sm text-slate-400">
                        No fields mapped yet for this document type.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex justify-between mt-3">
              <button
                onClick={() => resetMapping.mutate(activeDocType)}
                disabled={resetMapping.isPending}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                {resetMapping.isPending ? 'Resetting…' : 'Reset to Default'}
              </button>
              <button
                onClick={() => saveMapping.mutate({ docType: activeDocType, mapping: currentMapping })}
                disabled={saveMapping.isPending || Object.keys(currentMapping).length === 0}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                {saveMapping.isPending ? 'Saving…' : 'Save Mapping'}
              </button>
            </div>
          </>
        )}
      </div>

      {/* App Info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-3">Application</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between py-2 border-b border-slate-50">
            <span className="text-slate-500">Version</span>
            <span className="font-medium text-slate-700">1.0.0</span>
          </div>
          <div className="flex justify-between py-2 border-b border-slate-50">
            <span className="text-slate-500">AI Model</span>
            <span className="font-medium text-slate-700">Claude Sonnet 4.6</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-slate-500">Storage</span>
            <span className="font-medium text-slate-700">AWS S3</span>
          </div>
        </div>
      </div>
    </div>
  )
}
