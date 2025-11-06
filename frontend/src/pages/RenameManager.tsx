import { useState, useEffect } from 'react'
import {
  FileText,
  Eye,
  Save,
  AlertCircle,
  CheckSquare,
  Square,
  Sparkles,
  HardDriveDownload,
  Download,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import LoadingSpinner from '../components/LoadingSpinner'
import Modal from '../components/Modal'
import toast from 'react-hot-toast'
import {
  previewRename,
  applyRename,
  RenamePreview,
  saveMetadataSidecar,
  downloadMetadataSidecar,
  AssetMetadata,
} from '../services/api'

type MetadataFormState = {
  title: string
  description: string
  alt_text: string
  tags: string
  source?: string
  asset_type?: string
}

export default function RenameManager() {
  const { images, updateImage, selectedImageIds, toggleImageSelection, clearSelection, selectAll } = useApp()
  const [template, setTemplate] = useState('{description}_{date}_{index}')
  const [previews, setPreviews] = useState<RenamePreview[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [applying, setApplying] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [createBackups, setCreateBackups] = useState(true)
  const [metadataDrafts, setMetadataDrafts] = useState<Record<number, MetadataFormState>>({})
  const [metadataSavingId, setMetadataSavingId] = useState<number | null>(null)
  const [metadataDownloadingId, setMetadataDownloadingId] = useState<number | null>(null)

  const analyzedImages = images.filter(img => img.ai_description)
  const imagesToRename = selectedImageIds.length > 0
    ? selectedImageIds.filter(id => images.find(img => img.id === id && img.ai_description))
    : analyzedImages.map(img => img.id)

  const allSelected = analyzedImages.length > 0 && selectedImageIds.length === analyzedImages.length

  const formatMetadataSource = (source?: string) => {
    switch (source) {
      case 'sidecar':
        return 'Saved sidecar'
      case 'edited':
        return 'Edited metadata'
      case 'llava':
        return 'AI (LLaVA)'
      case 'fallback':
        return 'AI fallback'
      case 'manual':
        return 'Manual entry'
      default:
        return 'AI generated'
    }
  }

  const initializeMetadataDrafts = (items: RenamePreview[]) => {
    if (items.length === 0) {
      setMetadataDrafts({})
      return
    }

    const drafts: Record<number, MetadataFormState> = {}
    items.forEach(item => {
      drafts[item.image_id] = {
        title: item.metadata?.title ?? '',
        description: item.metadata?.description ?? '',
        alt_text: item.metadata?.alt_text ?? '',
        tags: (item.metadata?.tags ?? []).join(', '),
        source: item.metadata?.source,
        asset_type: item.metadata?.asset_type,
      }
    })
    setMetadataDrafts(drafts)
  }

  const handleMetadataChange = (
    imageId: number,
    field: 'title' | 'description' | 'alt_text' | 'tags',
    value: string
  ) => {
    setMetadataDrafts(prev => {
      const preview = previews.find(p => p.image_id === imageId)
      const base: MetadataFormState = prev[imageId] ?? {
        title: preview?.metadata.title ?? '',
        description: preview?.metadata.description ?? '',
        alt_text: preview?.metadata.alt_text ?? '',
        tags: (preview?.metadata.tags ?? []).join(', '),
        source: preview?.metadata.source,
        asset_type: preview?.metadata.asset_type,
      }

      return {
        ...prev,
        [imageId]: {
          ...base,
          [field]: value,
          source: 'edited',
        },
      }
    })
  }

  useEffect(() => {
    // Auto-generate preview when template or selection changes
    if (template && imagesToRename.length > 0) {
      handlePreview()
    } else {
      setPreviews([])
      setMetadataDrafts({})
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
      initializeMetadataDrafts(response.previews)
    } catch (error) {
      console.error('Preview error:', error)
      toast.error('Failed to generate preview')
      setPreviews([])
      setMetadataDrafts({})
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

  const handlePersistMetadata = async (imageId: number) => {
    const draft = metadataDrafts[imageId]
    if (!draft) {
      toast.error('No metadata available for this asset')
      return
    }

    const payload: AssetMetadata = {
      title: draft.title.trim(),
      description: draft.description.trim(),
      alt_text: draft.alt_text.trim(),
      tags: draft.tags
        .split(',')
        .map(tag => tag.trim())
        .filter(Boolean),
    }

    const toastId = `metadata-save-${imageId}`
    setMetadataSavingId(imageId)
    toast.loading('Saving metadata sidecar...', { id: toastId })

    try {
      const response = await saveMetadataSidecar(imageId, payload)
      const normalized: AssetMetadata = response.metadata
      toast.success('Metadata saved to sidecar', { id: toastId })

      setMetadataDrafts(prev => ({
        ...prev,
        [imageId]: {
          title: normalized.title ?? payload.title,
          description: normalized.description ?? payload.description,
          alt_text: normalized.alt_text ?? payload.alt_text,
          tags: (normalized.tags ?? payload.tags ?? []).join(', '),
          source: normalized.source ?? 'sidecar',
          asset_type: normalized.asset_type,
        },
      }))

      setPreviews(prev =>
        prev.map(preview =>
          preview.image_id === imageId
            ? {
                ...preview,
                metadata: {
                  ...preview.metadata,
                  title: normalized.title ?? payload.title,
                  description: normalized.description ?? payload.description,
                  alt_text: normalized.alt_text ?? payload.alt_text,
                  tags: normalized.tags ?? payload.tags ?? [],
                  source: normalized.source ?? 'sidecar',
                },
                sidecar_exists: true,
              }
            : preview
        )
      )

      updateImage(imageId, {
        ai_description: normalized.description ?? payload.description,
        ai_tags: normalized.tags ?? payload.tags ?? [],
        metadata_sidecar_exists: true,
      })
    } catch (error) {
      console.error('Metadata save error:', error)
      toast.error('Failed to save metadata sidecar', { id: toastId })
    } finally {
      setMetadataSavingId(null)
    }
  }

  const handleDownloadMetadata = async (imageId: number) => {
    const toastId = `metadata-download-${imageId}`
    setMetadataDownloadingId(imageId)
    toast.loading('Preparing metadata download...', { id: toastId })

    try {
      await downloadMetadataSidecar(imageId)
      toast.success('Metadata sidecar download started', { id: toastId })
    } catch (error) {
      console.error('Metadata download error:', error)
      toast.error('Failed to download metadata sidecar', { id: toastId })
    } finally {
      setMetadataDownloadingId(null)
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
              const isSelected = selectedImageIds.includes(preview.image_id)
              const metadataDraft = metadataDrafts[preview.image_id] ?? {
                title: preview.metadata?.title ?? '',
                description: preview.metadata?.description ?? '',
                alt_text: preview.metadata?.alt_text ?? '',
                tags: (preview.metadata?.tags ?? []).join(', '),
                source: preview.metadata?.source,
                asset_type: preview.metadata?.asset_type,
              }
              const metadataSource = metadataDraft.source || preview.metadata?.source
              const assetTypeLabel = metadataDraft.asset_type || preview.metadata?.asset_type

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

                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <div>
                          <label className="block text-xs font-semibold text-gray-500 mb-1">AI Title</label>
                          <input
                            type="text"
                            value={metadataDraft.title}
                            onChange={(e) => handleMetadataChange(preview.image_id, 'title', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Concise descriptive title"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-gray-500 mb-1">Tags</label>
                          <input
                            type="text"
                            value={metadataDraft.tags}
                            onChange={(e) => handleMetadataChange(preview.image_id, 'tags', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="tag1, tag2, tag3"
                          />
                        </div>
                        <div className="md:col-span-2">
                          <label className="block text-xs font-semibold text-gray-500 mb-1">Description</label>
                          <textarea
                            value={metadataDraft.description}
                            onChange={(e) => handleMetadataChange(preview.image_id, 'description', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={2}
                            placeholder="Short catalog description"
                          />
                        </div>
                        <div className="md:col-span-2">
                          <label className="block text-xs font-semibold text-gray-500 mb-1">Alt Text</label>
                          <textarea
                            value={metadataDraft.alt_text}
                            onChange={(e) => handleMetadataChange(preview.image_id, 'alt_text', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={2}
                            placeholder="Accessible summary for screen readers"
                          />
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                        <span className="font-semibold uppercase tracking-wide">
                          {formatMetadataSource(metadataSource)}
                        </span>
                        {assetTypeLabel && (
                          <span className="px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                            {assetTypeLabel.toUpperCase()}
                          </span>
                        )}
                        {preview.sidecar_exists && (
                          <span className="px-2 py-1 rounded-full bg-green-100 text-green-700">
                            Sidecar saved
                          </span>
                        )}
                      </div>

                      <div className="mt-4 flex flex-wrap gap-3">
                        <Button
                          variant="secondary"
                          icon={<HardDriveDownload className="w-4 h-4" />}
                          onClick={() => handlePersistMetadata(preview.image_id)}
                          loading={metadataSavingId === preview.image_id}
                        >
                          Save Sidecar
                        </Button>
                        <Button
                          variant="ghost"
                          icon={<Download className="w-4 h-4" />}
                          onClick={() => handleDownloadMetadata(preview.image_id)}
                          loading={metadataDownloadingId === preview.image_id}
                          disabled={!preview.sidecar_exists && metadataSavingId !== preview.image_id}
                        >
                          Download
                        </Button>
                      </div>
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
