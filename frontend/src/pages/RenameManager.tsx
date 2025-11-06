import { useState, useEffect } from 'react'
import { FileText, Eye, Save, AlertCircle, CheckSquare, Square, Sparkles } from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import LoadingSpinner from '../components/LoadingSpinner'
import Modal from '../components/Modal'
import toast from 'react-hot-toast'
import { previewRename, applyRename, RenamePreview } from '../services/api'

export default function RenameManager() {
  const { images, updateImage, selectedImageIds, toggleImageSelection, clearSelection, selectAll } = useApp()
  const [template, setTemplate] = useState('{description}_{date}_{index}')
  const [previews, setPreviews] = useState<RenamePreview[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [createBackups, setCreateBackups] = useState(true)

  const analyzedImages = images.filter(img => img.ai_description)
  const imagesToRename = selectedImageIds.length > 0
    ? selectedImageIds.filter(id => images.find(img => img.id === id && img.ai_description))
    : analyzedImages.map(img => img.id)

  const allSelected = analyzedImages.length > 0 && selectedImageIds.length === analyzedImages.length

  useEffect(() => {
    // Auto-generate preview when template or selection changes
    if (template && imagesToRename.length > 0) {
      handlePreview()
    } else {
      setPreviews([])
    }
  }, [template, selectedImageIds.length])

  const handlePreview = async () => {
    if (!template.trim()) {
      toast.error('Please enter a template')
      return
    }

    if (imagesToRename.length === 0) {
      toast.error('No analyzed images to rename')
      return
    }

    setLoadingPreview(true)

    try {
      const response = await previewRename(template, imagesToRename)
      setPreviews(response.previews)
    } catch (error) {
      console.error('Preview error:', error)
      toast.error('Failed to generate preview')
      setPreviews([])
    } finally {
      setLoadingPreview(false)
    }
  }

  const handleAutoRename = async () => {
    if (imagesToRename.length === 0) {
      toast.error('No analyzed images to rename')
      return
    }

    if (!confirm(`Auto-rename ${imagesToRename.length} images with AI-powered organization?\n\nThis will:\n- Use AI descriptions for filenames\n- Organize by year/month/scene/quality\n- Determine quality from file size and dimensions`)) {
      return
    }

    setApplying(true)

    try {
      toast.loading(`Auto-renaming ${imagesToRename.length} images...`, { id: 'auto-rename' })

      const response = await fetch('/api/rename/auto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(imagesToRename)
      })

      const data = await response.json()

      data.results.forEach((result: any) => {
        if (result.success) {
          updateImage(result.image_id, {
            current_filename: result.new_filename,
            filename: result.new_filename,
          })
        }
      })

      toast.success(`Successfully renamed ${data.succeeded} of ${data.total} images`, {
        id: 'auto-rename',
      })

      if (data.results.some((r: any) => !r.success)) {
        const errors = data.results.filter((r: any) => !r.success)
        errors.forEach((err: any) => {
          toast.error(`Failed to rename image ${err.image_id}: ${err.error}`)
        })
      }

      if (selectedImageIds.length > 0) {
        clearSelection()
      }
    } catch (error) {
      console.error('Auto-rename error:', error)
      toast.error('Error auto-renaming images', { id: 'auto-rename' })
    } finally {
      setApplying(false)
    }
  }

  const handleApplyRename = async () => {
    setApplying(true)
    setShowConfirmModal(false)

    try {
      toast.loading(`Renaming ${imagesToRename.length} images...`, { id: 'rename' })

      const response = await applyRename(template, imagesToRename, createBackups)

      response.results.forEach(result => {
        if (result.success && result.new_filename) {
          updateImage(result.image_id, {
            current_filename: result.new_filename,
            filename: result.new_filename,
          })
        }
      })

      toast.success(`Successfully renamed ${response.succeeded} of ${response.total} images`, {
        id: 'rename',
      })

      if (response.results.some(r => !r.success)) {
        const errors = response.results.filter(r => !r.success)
        errors.forEach(err => {
          toast.error(`Failed to rename image ${err.image_id}: ${err.error}`)
        })
      }

      if (selectedImageIds.length > 0) {
        clearSelection()
      }

      // Refresh preview with new names
      await handlePreview()
    } catch (error) {
      console.error('Rename error:', error)
      toast.error('Error renaming images', { id: 'rename' })
    } finally {
      setApplying(false)
    }
  }

  const insertVariable = (variable: string) => {
    setTemplate(prev => prev + variable)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Rename Manager</h1>
            <p className="text-gray-600 mt-1">
              Batch rename images using AI analysis and custom templates
            </p>
          </div>

          {analyzedImages.length > 0 && (
            <Button
              variant="primary"
              size="lg"
              icon={<Sparkles className="w-5 h-5" />}
              onClick={handleAutoRename}
              disabled={applying || imagesToRename.length === 0}
              loading={applying}
              className="!bg-gradient-to-r !from-purple-600 !to-blue-600 hover:!from-purple-700 hover:!to-blue-700"
            >
              AI Auto-Rename {imagesToRename.length > 0 && `(${imagesToRename.length})`}
            </Button>
          )}
        </div>
      </div>

      {/* Template Input */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Naming Template
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Pattern
            </label>
            <input
              type="text"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="{description}_{date}_{index}"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Quick Insert Variables:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => insertVariable('{description}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{description}'}
              </button>
              <button
                onClick={() => insertVariable('{tags}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{tags}'}
              </button>
              <button
                onClick={() => insertVariable('{scene}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{scene}'}
              </button>
              <button
                onClick={() => insertVariable('{date}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{date}'}
              </button>
              <button
                onClick={() => insertVariable('{time}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{time}'}
              </button>
              <button
                onClick={() => insertVariable('{index}')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                {'{index}'}
              </button>
              <button
                onClick={() => insertVariable('_')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                _
              </button>
              <button
                onClick={() => insertVariable('-')}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-sm"
              >
                -
              </button>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-900 mb-2">Available Variables:</p>
            <ul className="text-sm text-blue-800 space-y-1">
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{description}'}</code> - AI-generated description (slug format)</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{tags}'}</code> - Top AI tags (slug format)</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{scene}'}</code> - Scene type detected by AI</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{date}'}</code> - Current date (YYYYMMDD)</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{time}'}</code> - Current time (HHMMSS)</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{index}'}</code> - Sequential number (001, 002, ...)</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">{'{original}'}</code> - Original filename (without extension)</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Selection Controls */}
      {analyzedImages.length > 0 && (
        <div className="mb-6 flex items-center justify-between bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-4">
            <button
              onClick={allSelected ? clearSelection : selectAll}
              className="flex items-center gap-2 text-gray-700 hover:text-gray-900"
            >
              {allSelected ? (
                <CheckSquare className="w-5 h-5 text-blue-600" />
              ) : (
                <Square className="w-5 h-5" />
              )}
              <span className="text-sm font-medium">
                {allSelected ? 'Deselect All' : 'Select All'}
              </span>
            </button>

            {selectedImageIds.length > 0 && (
              <span className="text-sm text-gray-600">
                {selectedImageIds.length} of {analyzedImages.length} selected
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={createBackups}
                onChange={(e) => setCreateBackups(e.target.checked)}
                className="rounded"
              />
              Create backups
            </label>

            <Button
              variant="secondary"
              icon={<Eye className="w-5 h-5" />}
              onClick={handlePreview}
              loading={loadingPreview}
              disabled={loadingPreview || !template || imagesToRename.length === 0}
            >
              Preview
            </Button>

            <Button
              variant="primary"
              icon={<Save className="w-5 h-5" />}
              onClick={() => setShowConfirmModal(true)}
              disabled={previews.length === 0 || applying}
              loading={applying}
            >
              Apply Rename
            </Button>
          </div>
        </div>
      )}

      {/* No images message */}
      {images.length === 0 && (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg mb-2">No images uploaded yet</p>
          <p className="text-gray-500">
            Upload and analyze images in the Gallery first
          </p>
        </div>
      )}

      {/* No analyzed images message */}
      {images.length > 0 && analyzedImages.length === 0 && (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <Sparkles className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg mb-2">No analyzed images</p>
          <p className="text-gray-500">
            Analyze your images in the Gallery before renaming
          </p>
        </div>
      )}

      {/* Loading state */}
      {loadingPreview && (
        <div className="mb-6">
          <LoadingSpinner text="Generating preview..." />
        </div>
      )}

      {/* Preview List */}
      {previews.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b bg-gray-50">
            <h3 className="font-semibold text-gray-900">
              Rename Preview ({previews.length} {previews.length === 1 ? 'image' : 'images'})
            </h3>
          </div>

          <div className="divide-y max-h-[600px] overflow-y-auto">
            {previews.map((preview) => {
              const image = images.find(img => img.id === preview.image_id)
              const isSelected = selectedImageIds.includes(preview.image_id)

              return (
                <div
                  key={preview.image_id}
                  className={`p-4 hover:bg-gray-50 transition-colors ${
                    isSelected ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <button
                      onClick={() => toggleImageSelection(preview.image_id)}
                      className={`mt-1 w-5 h-5 rounded border-2 flex-shrink-0 transition-colors ${
                        isSelected
                          ? 'bg-blue-600 border-blue-600'
                          : 'bg-white border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {isSelected && <span className="text-white text-xs">✓</span>}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm text-gray-500">Current:</span>
                        <span className="text-sm font-mono text-gray-700 truncate">
                          {preview.current_filename}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">New:</span>
                        <span className="text-sm font-mono text-green-700 font-medium truncate">
                          {preview.proposed_filename}
                        </span>
                      </div>

                      {image?.ai_description && (
                        <div className="mt-2 text-xs text-gray-600 line-clamp-1">
                          {image.ai_description}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Confirm Batch Rename"
        size="md"
        footer={
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setShowConfirmModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleApplyRename}
              icon={<Save className="w-5 h-5" />}
            >
              Confirm Rename
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium mb-1">You are about to rename {imagesToRename.length} images</p>
              <p>
                {createBackups
                  ? 'Original filenames will be backed up.'
                  : 'Original filenames will NOT be backed up. This action cannot be undone.'}
              </p>
            </div>
          </div>

          <div className="text-sm text-gray-600">
            <p className="font-medium mb-2">Template:</p>
            <code className="block bg-gray-100 p-2 rounded">{template}</code>
          </div>

          <p className="text-sm text-gray-600">
            Are you sure you want to continue?
          </p>
        </div>
      </Modal>
    </div>
  )
}
