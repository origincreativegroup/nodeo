import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Save, CheckCircle, XCircle, Loader } from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import NextcloudSettings from '../components/NextcloudSettings'
import toast from 'react-hot-toast'
import { testOllamaConnection } from '../services/api'

export default function Settings() {
  const { settings, updateSettings } = useApp()
  const [formData, setFormData] = useState(settings)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setFormData(settings)
  }, [settings])

  useEffect(() => {
    const changed = JSON.stringify(formData) !== JSON.stringify(settings)
    setHasChanges(changed)
  }, [formData, settings])

  const handleInputChange = (field: keyof typeof formData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setTestResult(null)
  }

  const handleTestConnection = async () => {
    if (!formData.ollamaHost) {
      toast.error('Please enter Ollama host URL')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const result = await testOllamaConnection(formData.ollamaHost)

      if (result.success) {
        setTestResult({
          success: true,
          message: `Connected! Found ${result.models?.length || 0} models available`
        })
        toast.success('Connection successful!')
      } else {
        setTestResult({
          success: false,
          message: result.error || 'Connection failed'
        })
        toast.error('Connection failed')
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Unable to connect to Ollama server'
      })
      toast.error('Connection test failed')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = () => {
    updateSettings(formData)
    toast.success('Settings saved successfully!')
    setHasChanges(false)
  }

  const handleReset = () => {
    setFormData(settings)
    setTestResult(null)
    toast.success('Changes discarded')
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">
          Configure AI models, storage integrations, and application preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* Ollama Configuration */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b bg-gray-50">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5" />
              Ollama AI Configuration
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Configure connection to your local Ollama instance for AI image analysis
            </p>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ollama Host URL
              </label>
              <input
                type="text"
                value={formData.ollamaHost}
                onChange={(e) => handleInputChange('ollamaHost', e.target.value)}
                placeholder="http://192.168.50.248:11434"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                URL of your Ollama server (typically http://localhost:11434 or network address)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model Name
              </label>
              <input
                type="text"
                value={formData.ollamaModel}
                onChange={(e) => handleInputChange('ollamaModel', e.target.value)}
                placeholder="llava"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Vision model to use (llava, llava:13b, llava:34b, etc.)
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={handleTestConnection}
                loading={testing}
                disabled={testing || !formData.ollamaHost}
              >
                Test Connection
              </Button>

              {testResult && (
                <div className={`flex items-center gap-2 text-sm ${
                  testResult.success ? 'text-green-700' : 'text-red-700'
                }`}>
                  {testResult.success ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <XCircle className="w-4 h-4" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}

              {testing && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Loader className="w-4 h-4 animate-spin" />
                  <span>Testing connection...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Nextcloud Configuration */}
        <NextcloudSettings />

        {/* Cloudflare Configuration */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b bg-gray-50">
            <h2 className="text-xl font-semibold text-gray-900">Cloudflare Storage</h2>
            <p className="text-sm text-gray-600 mt-1">
              Configure R2 and Stream for cloud storage and video hosting
            </p>
          </div>

          <div className="p-6 space-y-6">
            <div className="border-b pb-6">
              <h3 className="font-medium text-gray-900 mb-4">Cloudflare R2 (S3-Compatible Storage)</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Account ID
                  </label>
                  <input
                    type="text"
                    value={formData.cloudflareR2AccountId}
                    onChange={(e) => handleInputChange('cloudflareR2AccountId', e.target.value)}
                    placeholder="your-account-id"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Access Key ID
                  </label>
                  <input
                    type="text"
                    value={formData.cloudflareR2AccessKeyId}
                    onChange={(e) => handleInputChange('cloudflareR2AccessKeyId', e.target.value)}
                    placeholder="access-key-id"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Secret Access Key
                  </label>
                  <input
                    type="password"
                    value={formData.cloudflareR2SecretAccessKey}
                    onChange={(e) => handleInputChange('cloudflareR2SecretAccessKey', e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Bucket Name
                  </label>
                  <input
                    type="text"
                    value={formData.cloudflareR2Bucket}
                    onChange={(e) => handleInputChange('cloudflareR2Bucket', e.target.value)}
                    placeholder="my-bucket"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.cloudflareR2Enabled}
                      onChange={(e) => handleInputChange('cloudflareR2Enabled', e.target.checked)}
                      className="rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Enable R2 storage
                    </span>
                  </label>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-4">Cloudflare Stream (Video Hosting)</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    API Token
                  </label>
                  <input
                    type="password"
                    value={formData.cloudflareStreamApiToken}
                    onChange={(e) => handleInputChange('cloudflareStreamApiToken', e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.cloudflareStreamEnabled}
                      onChange={(e) => handleInputChange('cloudflareStreamEnabled', e.target.checked)}
                      className="rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Enable Stream integration
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        {hasChanges && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-yellow-800">
              <SettingsIcon className="w-5 h-5" />
              <span className="font-medium">You have unsaved changes</span>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={handleReset}>
                Discard Changes
              </Button>
              <Button
                variant="primary"
                icon={<Save className="w-5 h-5" />}
                onClick={handleSave}
              >
                Save Settings
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
