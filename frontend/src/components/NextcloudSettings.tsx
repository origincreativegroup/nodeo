import { useState, useEffect } from 'react'
import { Cloud, CheckCircle, XCircle, Loader, Save, RefreshCw } from 'lucide-react'
import Button from './Button'
import toast from 'react-hot-toast'
import {
  getNextcloudSettings,
  saveNextcloudSettings,
  testNextcloudConnection,
  NextcloudSettings as NextcloudSettingsType,
  NextcloudSettingsRequest
} from '../services/api'

export default function NextcloudSettings() {
  const [settings, setSettings] = useState<NextcloudSettingsType | null>(null)
  const [formData, setFormData] = useState<NextcloudSettingsRequest>({
    server_url: '',
    username: '',
    password: '',
    base_path: '/jspow',
    auto_sync_enabled: true,
    sync_on_upload: false,
    sync_on_rename: true,
    sync_strategy: 'mirror'
  })
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await getNextcloudSettings()
      setSettings(data)

      if (data.configured) {
        setFormData({
          server_url: data.server_url || '',
          username: data.username || '',
          password: '', // Don't populate password for security
          base_path: data.base_path || '/jspow',
          auto_sync_enabled: data.auto_sync_enabled ?? true,
          sync_on_upload: data.sync_on_upload ?? false,
          sync_on_rename: data.sync_on_rename ?? true,
          sync_strategy: data.sync_strategy || 'mirror'
        })
      }
    } catch (error) {
      console.error('Failed to load Nextcloud settings:', error)
      toast.error('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof NextcloudSettingsRequest, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setHasChanges(true)
  }

  const handleSave = async () => {
    if (!formData.server_url || !formData.username) {
      toast.error('Please fill in server URL and username')
      return
    }

    // If password is empty and settings exist, don't update password
    if (!formData.password && settings?.configured) {
      toast.error('Please enter password')
      return
    }

    try {
      setSaving(true)
      await saveNextcloudSettings(formData)
      toast.success('Settings saved successfully!')
      setHasChanges(false)
      await loadSettings() // Reload to get updated connection status
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!settings?.configured) {
      toast.error('Please save settings first')
      return
    }

    try {
      setTesting(true)
      const result = await testNextcloudConnection()

      if (result.success && result.connected) {
        toast.success('Connection successful!')
        await loadSettings() // Reload to get updated connection status
      } else {
        toast.error(result.message || 'Connection failed')
      }
    } catch (error) {
      console.error('Connection test failed:', error)
      toast.error('Connection test failed')
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 flex items-center justify-center">
          <Loader className="w-6 h-6 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-600">Loading settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Cloud className="w-5 h-5" />
              Nextcloud Integration
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Connect to your Nextcloud instance for automatic file synchronization
            </p>
          </div>

          {settings?.is_connected && (
            <div className="flex items-center gap-2 text-green-700 bg-green-50 px-3 py-1.5 rounded-full">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Connected</span>
            </div>
          )}

          {settings?.configured && !settings.is_connected && (
            <div className="flex items-center gap-2 text-red-700 bg-red-50 px-3 py-1.5 rounded-full">
              <XCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Disconnected</span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Connection Settings */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Connection Settings</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Server URL *
            </label>
            <input
              type="text"
              value={formData.server_url}
              onChange={(e) => handleInputChange('server_url', e.target.value)}
              placeholder="https://nextcloud.lan"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Full URL to your Nextcloud instance
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Username *
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                placeholder="admin"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password *
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                placeholder={settings?.configured ? '••••••••' : 'Enter password'}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Base Path
            </label>
            <input
              type="text"
              value={formData.base_path}
              onChange={(e) => handleInputChange('base_path', e.target.value)}
              placeholder="/jspow"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Base folder path in Nextcloud where files will be stored
            </p>
          </div>
        </div>

        {/* Sync Settings */}
        <div className="space-y-4 pt-4 border-t">
          <h3 className="font-medium text-gray-900">Sync Settings</h3>

          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={formData.auto_sync_enabled}
                onChange={(e) => handleInputChange('auto_sync_enabled', e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Enable Auto-Sync</span>
                <p className="text-xs text-gray-500">Automatically sync files to Nextcloud</p>
              </div>
            </label>

            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={formData.sync_on_upload}
                onChange={(e) => handleInputChange('sync_on_upload', e.target.checked)}
                disabled={!formData.auto_sync_enabled}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Sync on Upload</span>
                <p className="text-xs text-gray-500">Sync files immediately after upload</p>
              </div>
            </label>

            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={formData.sync_on_rename}
                onChange={(e) => handleInputChange('sync_on_rename', e.target.checked)}
                disabled={!formData.auto_sync_enabled}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Sync on Rename</span>
                <p className="text-xs text-gray-500">Sync files when renamed (recommended)</p>
              </div>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sync Strategy
            </label>
            <select
              value={formData.sync_strategy}
              onChange={(e) => handleInputChange('sync_strategy', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="mirror">Mirror - Keep Nextcloud in sync with local</option>
              <option value="backup">Backup - Upload only, never delete</option>
              <option value="primary">Primary - Nextcloud is primary source</option>
            </select>
          </div>
        </div>

        {/* Connection Status */}
        {settings?.configured && (
          <div className="pt-4 border-t">
            <h3 className="font-medium text-gray-900 mb-3">Connection Status</h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className={`font-medium ${settings.is_connected ? 'text-green-700' : 'text-red-700'}`}>
                  {settings.is_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {settings.last_connection_test && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Test:</span>
                  <span className="text-gray-900">
                    {new Date(settings.last_connection_test).toLocaleString()}
                  </span>
                </div>
              )}
              {settings.total_synced !== undefined && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Synced:</span>
                  <span className="text-gray-900">{settings.total_synced} files</span>
                </div>
              )}
              {settings.last_sync_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Sync:</span>
                  <span className="text-gray-900">
                    {new Date(settings.last_sync_at).toLocaleString()}
                  </span>
                </div>
              )}
              {settings.connection_error && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <span className="text-red-700 text-xs">{settings.connection_error}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t">
          <Button
            variant="primary"
            icon={<Save className="w-4 h-4" />}
            onClick={handleSave}
            loading={saving}
            disabled={saving || !hasChanges}
          >
            Save Settings
          </Button>

          {settings?.configured && (
            <Button
              variant="secondary"
              icon={<RefreshCw className={`w-4 h-4 ${testing ? 'animate-spin' : ''}`} />}
              onClick={handleTest}
              loading={testing}
              disabled={testing || hasChanges}
            >
              Test Connection
            </Button>
          )}

          {hasChanges && (
            <Button
              variant="secondary"
              onClick={() => {
                loadSettings()
                setHasChanges(false)
                toast.success('Changes discarded')
              }}
            >
              Discard
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
