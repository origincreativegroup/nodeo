import { useState } from 'react'
import { Cloud, Upload, CheckCircle, XCircle, Loader, CheckSquare, Square } from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import Modal from '../components/Modal'
import toast from 'react-hot-toast'
import { uploadToNextcloud, uploadToR2 } from '../services/api'

export default function StorageManager() {
  const { images, settings, selectedImageIds, toggleImageSelection, clearSelection, selectAll } = useApp()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadTarget, setUploadTarget] = useState<'nextcloud' | 'r2' | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadPath, setUploadPath] = useState('')

  const analyzedImages = images.filter(img => img.ai_description)
  const imagesToUpload = selectedImageIds.length > 0
    ? selectedImageIds.filter(id => images.find(img => img.id === id && img.ai_description))
    : analyzedImages.map(img => img.id)

  const allSelected = analyzedImages.length > 0 && selectedImageIds.length === analyzedImages.length

  const handleOpenUploadModal = (target: 'nextcloud' | 'r2') => {
    if (imagesToUpload.length === 0) {
      toast.error('No analyzed images to upload')
      return
    }

    setUploadTarget(target)
    setUploadPath(target === 'nextcloud' ? '/Photos/' : 'images/')
    setShowUploadModal(true)
  }

  const handleUpload = async () => {
    if (!uploadTarget || !uploadPath.trim()) {
      toast.error('Please enter a path')
      return
    }

    if (uploadTarget === 'nextcloud' && !settings.nextcloudEnabled) {
      toast.error('Nextcloud integration is not enabled. Configure it in Settings.')
      return
    }

    if (uploadTarget === 'r2' && !settings.cloudflareR2Enabled) {
      toast.error('Cloudflare R2 is not enabled. Configure it in Settings.')
      return
    }

    setUploading(true)
    setShowUploadModal(false)

    try {
      toast.loading(`Uploading ${imagesToUpload.length} images to ${uploadTarget === 'nextcloud' ? 'Nextcloud' : 'R2'}...`, { id: 'upload' })

      let succeeded = 0
      let failed = 0

      for (const imageId of imagesToUpload) {
        try {
          if (uploadTarget === 'nextcloud') {
            await uploadToNextcloud(imageId, uploadPath)
          } else {
            await uploadToR2(imageId, uploadPath)
          }
          succeeded++
        } catch (error) {
          console.error(`Failed to upload image ${imageId}:`, error)
          failed++
        }
      }

      toast.success(`Successfully uploaded ${succeeded} of ${imagesToUpload.length} images`, {
        id: 'upload',
      })

      if (failed > 0) {
        toast.error(`Failed to upload ${failed} images`)
      }

      if (selectedImageIds.length > 0) {
        clearSelection()
      }
    } catch (error) {
      console.error('Upload error:', error)
      toast.error('Error uploading images', { id: 'upload' })
    } finally {
      setUploading(false)
      setUploadTarget(null)
      setUploadPath('')
    }
  }

  const isNextcloudConfigured = settings.nextcloudEnabled && settings.nextcloudUrl && settings.nextcloudUsername
  const isR2Configured = settings.cloudflareR2Enabled && settings.cloudflareR2AccountId && settings.cloudflareR2AccessKeyId
  const isStreamConfigured = settings.cloudflareStreamEnabled && settings.cloudflareStreamApiToken

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Storage Manager</h1>
        <p className="text-gray-600 mt-1">
          Upload and sync images to cloud storage providers
        </p>
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

          <div className="text-sm text-gray-600">
            {selectedImageIds.length > 0
              ? `${selectedImageIds.length} images selected for upload`
              : `${analyzedImages.length} analyzed images available`}
          </div>
        </div>
      )}

      {/* Storage Providers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Nextcloud */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <Cloud className="w-12 h-12 text-blue-600" />
              {isNextcloudConfigured ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <h2 className="text-xl font-semibold mb-2">Nextcloud</h2>
            <p className="text-gray-600 mb-4 text-sm">
              Organize and sync images with your Nextcloud instance
            </p>

            {isNextcloudConfigured ? (
              <div className="space-y-2">
                <p className="text-xs text-gray-500">
                  Connected to: {settings.nextcloudUrl}
                </p>
                <Button
                  variant="primary"
                  icon={<Upload className="w-4 h-4" />}
                  onClick={() => handleOpenUploadModal('nextcloud')}
                  disabled={uploading || imagesToUpload.length === 0}
                  className="w-full"
                >
                  Upload Images
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-red-600 mb-2">
                  Not configured
                </p>
                <Button
                  variant="secondary"
                  onClick={() => window.location.href = '/settings'}
                  className="w-full"
                >
                  Configure
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Cloudflare R2 */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <Cloud className="w-12 h-12 text-orange-600" />
              {isR2Configured ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <h2 className="text-xl font-semibold mb-2">Cloudflare R2</h2>
            <p className="text-gray-600 mb-4 text-sm">
              Store images in S3-compatible Cloudflare R2 bucket
            </p>

            {isR2Configured ? (
              <div className="space-y-2">
                <p className="text-xs text-gray-500">
                  Bucket: {settings.cloudflareR2Bucket || 'Not set'}
                </p>
                <Button
                  variant="primary"
                  icon={<Upload className="w-4 h-4" />}
                  onClick={() => handleOpenUploadModal('r2')}
                  disabled={uploading || imagesToUpload.length === 0}
                  className="w-full"
                >
                  Upload Images
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-red-600 mb-2">
                  Not configured
                </p>
                <Button
                  variant="secondary"
                  onClick={() => window.location.href = '/settings'}
                  className="w-full"
                >
                  Configure
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Cloudflare Stream */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <Cloud className="w-12 h-12 text-purple-600" />
              {isStreamConfigured ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : (
                <XCircle className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <h2 className="text-xl font-semibold mb-2">Cloudflare Stream</h2>
            <p className="text-gray-600 mb-4 text-sm">
              Upload and host videos on Cloudflare Stream
            </p>

            {isStreamConfigured ? (
              <div className="space-y-2">
                <p className="text-xs text-gray-500">
                  Status: Enabled
                </p>
                <Button
                  variant="primary"
                  icon={<Upload className="w-4 h-4" />}
                  disabled
                  className="w-full"
                >
                  Coming Soon
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-red-600 mb-2">
                  Not configured
                </p>
                <Button
                  variant="secondary"
                  onClick={() => window.location.href = '/settings'}
                  className="w-full"
                >
                  Configure
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Image List */}
      {analyzedImages.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b bg-gray-50">
            <h3 className="font-semibold text-gray-900">
              Available Images ({analyzedImages.length})
            </h3>
          </div>

          <div className="divide-y max-h-[500px] overflow-y-auto">
            {analyzedImages.map((image) => {
              const isSelected = selectedImageIds.includes(image.id)

              return (
                <div
                  key={image.id}
                  className={`p-4 hover:bg-gray-50 transition-colors ${
                    isSelected ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => toggleImageSelection(image.id)}
                      className={`w-5 h-5 rounded border-2 flex-shrink-0 transition-colors ${
                        isSelected
                          ? 'bg-blue-600 border-blue-600'
                          : 'bg-white border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {isSelected && <span className="text-white text-xs">✓</span>}
                    </button>

                    <img
                      src={`/api/images/${image.id}/thumbnail`}
                      alt={image.current_filename}
                      className="w-16 h-16 object-cover rounded"
                      onError={(e) => {
                        e.currentTarget.src = `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="%23e5e7eb"/></svg>`
                      }}
                    />

                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">
                        {image.current_filename}
                      </h4>
                      {image.ai_description && (
                        <p className="text-sm text-gray-600 line-clamp-1">
                          {image.ai_description}
                        </p>
                      )}
                      {image.ai_tags && image.ai_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {image.ai_tags.slice(0, 3).map((tag, idx) => (
                            <span
                              key={idx}
                              className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="text-sm text-gray-500">
                      {image.width && image.height && (
                        <span>{image.width}×{image.height}</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* No images message */}
      {analyzedImages.length === 0 && (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <Cloud className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg mb-2">No analyzed images</p>
          <p className="text-gray-500">
            Upload and analyze images in the Gallery before uploading to storage
          </p>
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title={`Upload to ${uploadTarget === 'nextcloud' ? 'Nextcloud' : 'Cloudflare R2'}`}
        size="md"
        footer={
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setShowUploadModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              icon={<Upload className="w-5 h-5" />}
              onClick={handleUpload}
              disabled={!uploadPath.trim()}
            >
              Upload {imagesToUpload.length} {imagesToUpload.length === 1 ? 'Image' : 'Images'}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {uploadTarget === 'nextcloud' ? 'Remote Path' : 'Object Key Prefix'}
            </label>
            <input
              type="text"
              value={uploadPath}
              onChange={(e) => setUploadPath(e.target.value)}
              placeholder={uploadTarget === 'nextcloud' ? '/Photos/' : 'images/'}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              {uploadTarget === 'nextcloud'
                ? 'Path in Nextcloud where images will be uploaded (e.g., /Photos/)'
                : 'Prefix for object keys in R2 bucket (e.g., images/)'}
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              {imagesToUpload.length} {imagesToUpload.length === 1 ? 'image' : 'images'} will be uploaded
              {selectedImageIds.length > 0 ? ' (selected)' : ' (all analyzed images)'}
            </p>
          </div>
        </div>
      </Modal>

      {/* Uploading overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md">
            <div className="flex items-center gap-4">
              <Loader className="w-8 h-8 animate-spin text-blue-600" />
              <div>
                <h3 className="font-semibold text-gray-900">Uploading images...</h3>
                <p className="text-sm text-gray-600">This may take a moment</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
