/**
 * Ollama AI Configuration Component
 */

import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon,
  CheckCircle,
  XCircle,
  Loader,
  AlertCircle,
  RefreshCw,
  ChevronDown,
} from 'lucide-react'
import Button from './Button'
import toast from 'react-hot-toast'

interface OllamaSettings {
  host: string
  model: string
  timeout: number
}

interface OllamaSettingsResponse extends OllamaSettings {
  available_models: string[]
}

interface TestResult {
  success: boolean
  message: string
  available_models?: string[]
  server_version?: string
  suggestion?: string
}

export default function OllamaSettings() {
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<OllamaSettings>({
    host: '',
    model: '',
    timeout: 120,
  })
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [formData, setFormData] = useState(settings)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [])

  useEffect(() => {
    const changed = JSON.stringify(formData) !== JSON.stringify(settings)
    setHasChanges(changed)
  }, [formData, settings])

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/settings/ollama')
      if (!response.ok) throw new Error('Failed to fetch settings')

      const data: OllamaSettingsResponse = await response.json()
      setSettings({
        host: data.host,
        model: data.model,
        timeout: data.timeout,
      })
      setFormData({
        host: data.host,
        model: data.model,
        timeout: data.timeout,
      })
      setAvailableModels(data.available_models)
    } catch (error) {
      console.error('Error fetching Ollama settings:', error)
      toast.error('Failed to load Ollama settings')
    } finally {
      setLoading(false)
    }
  }

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)

    try {
      const response = await fetch('/api/settings/ollama/test', {
        method: 'POST',
      })
      const result: TestResult = await response.json()

      setTestResult(result)

      if (result.success) {
        toast.success('Connection successful!')
        // Update available models if returned
        if (result.available_models) {
          setAvailableModels(result.available_models)
        }
      } else {
        toast.error('Connection failed')
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to connect to server',
        suggestion: 'Check that the backend server is running',
      })
      toast.error('Connection test failed')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)

    try {
      const response = await fetch('/api/settings/ollama', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ollama_host: formData.host,
          ollama_model: formData.model,
          ollama_timeout: formData.timeout,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update settings')
      }

      const updated: OllamaSettings = await response.json()
      setSettings(updated)
      setFormData(updated)
      setHasChanges(false)
      toast.success('Settings saved successfully!')
      setTestResult(null)
    } catch (error) {
      console.error('Error saving settings:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setFormData(settings)
    setTestResult(null)
    toast.success('Changes discarded')
  }

  const handleRefreshModels = async () => {
    try {
      const response = await fetch('/api/settings/ollama')
      if (!response.ok) throw new Error('Failed to fetch models')

      const data: OllamaSettingsResponse = await response.json()
      setAvailableModels(data.available_models)
      toast.success(`Found ${data.available_models.length} models`)
    } catch (error) {
      toast.error('Failed to refresh model list')
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-8">
          <Loader className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Loading Ollama settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b bg-gray-50">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5" />
          Ollama AI Configuration
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Configure connection to your Ollama instance for AI-powered image analysis
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Host URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ollama Server URL
          </label>
          <input
            type="text"
            value={formData.host}
            onChange={(e) => setFormData({ ...formData, host: e.target.value })}
            placeholder="http://localhost:11434"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-1">
            URL of your Ollama server (e.g., http://localhost:11434 or http://192.168.1.100:11434)
          </p>
        </div>

        {/* Model Selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Vision Model
            </label>
            <button
              onClick={handleRefreshModels}
              className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
              title="Refresh available models"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>

          {availableModels.length > 0 ? (
            <div className="relative">
              <select
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                className="w-full appearance-none px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              >
                {availableModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          ) : (
            <input
              type="text"
              value={formData.model}
              onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              placeholder="llava"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          )}

          <p className="text-xs text-gray-500 mt-1">
            Vision-capable models: llava, qwen2-vl, minicpm-v, bakllava
          </p>
        </div>

        {/* Timeout */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Request Timeout (seconds)
          </label>
          <input
            type="number"
            min="10"
            max="600"
            value={formData.timeout}
            onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 120 })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-1">
            Maximum time to wait for model responses (10-600 seconds)
          </p>
        </div>

        {/* Test Connection */}
        <div className="pt-2">
          <Button
            variant="secondary"
            onClick={handleTestConnection}
            loading={testing}
            disabled={testing || !formData.host}
            className="mb-3"
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </Button>

          {testResult && (
            <div
              className={`p-4 rounded-lg border ${
                testResult.success
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-start gap-2">
                {testResult.success ? (
                  <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p
                    className={`text-sm font-medium ${
                      testResult.success ? 'text-green-800' : 'text-red-800'
                    }`}
                  >
                    {testResult.message}
                  </p>
                  {testResult.server_version && (
                    <p className="text-xs text-green-700 mt-1">
                      Server version: {testResult.server_version}
                    </p>
                  )}
                  {testResult.available_models && testResult.available_models.length > 0 && (
                    <p className="text-xs text-green-700 mt-1">
                      Available models: {testResult.available_models.join(', ')}
                    </p>
                  )}
                  {testResult.suggestion && (
                    <p className="text-xs text-red-700 mt-1 flex items-start gap-1">
                      <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                      {testResult.suggestion}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Model Recommendations */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">
            Model Recommendations
          </h4>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>• <strong>llava</strong> - Best overall balance of speed and quality</li>
            <li>• <strong>llava:13b</strong> - Higher quality, slower inference</li>
            <li>• <strong>qwen2-vl</strong> - Excellent for detailed image analysis</li>
            <li>• <strong>minicpm-v</strong> - Fast and efficient for basic tasks</li>
          </ul>
          <p className="text-xs text-blue-700 mt-2">
            Install models with: <code className="bg-blue-100 px-1 rounded">ollama pull model-name</code>
          </p>
        </div>

        {/* Save/Reset Actions */}
        {hasChanges && (
          <div className="flex items-center justify-between pt-4 border-t">
            <p className="text-sm text-gray-600 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-yellow-600" />
              You have unsaved changes
            </p>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={handleReset} disabled={saving}>
                Discard
              </Button>
              <Button variant="primary" onClick={handleSave} loading={saving}>
                Save Changes
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
