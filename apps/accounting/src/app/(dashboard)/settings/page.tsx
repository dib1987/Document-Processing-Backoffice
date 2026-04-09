'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth, useOrganization } from '@clerk/nextjs'
import { settingsApi, setAuthHeaders } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { Save, Eye, EyeOff } from 'lucide-react'

function useHubspotSettings() {
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  return useQuery({
    queryKey: ['hubspot-settings'],
    queryFn: async () => {
      const token = await getToken()
      if (token && organization?.id) setAuthHeaders(token, organization.id)
      const res = await settingsApi.getHubspot()
      return res.data
    },
  })
}

export default function SettingsPage() {
  const { data: settings } = useHubspotSettings()
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const { toast } = useToast()
  const { getToken } = useAuth()
  const { organization } = useOrganization()
  const queryClient = useQueryClient()

  const saveHubspot = useMutation({
    mutationFn: async (key: string) => {
      const token = await getToken()
      if (token && organization?.id) setAuthHeaders(token, organization.id)
      return settingsApi.saveHubspot(key)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hubspot-settings'] })
      toast({ title: 'HubSpot API key saved' })
      setApiKey('')
    },
    onError: () => toast({ title: 'Failed to save', variant: 'destructive' }),
  })

  return (
    <div className="max-w-2xl space-y-6">
      {/* HubSpot Integration */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-1">HubSpot Integration</h2>
        <p className="text-sm text-slate-400 mb-4">Connect your HubSpot account to automatically push processed documents to your CRM.</p>

        {settings?.hubspot_connected && (
          <div className="flex items-center gap-2 mb-4 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
            <div className="w-2 h-2 bg-emerald-500 rounded-full" />
            <span className="text-sm text-emerald-700 font-medium">HubSpot is connected</span>
          </div>
        )}

        <label className="block text-sm font-medium text-slate-700 mb-2">
          {settings?.hubspot_connected ? 'Update API Key' : 'HubSpot Private App API Key'}
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
