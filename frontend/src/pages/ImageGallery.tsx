import { useState } from 'react'
import { Upload, Sparkles, Edit2 } from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import LoadingSpinner from '../components/LoadingSpinner'
import Modal from '../components/Modal'
import ImageSelectionPanel from '../components/ImageSelectionPanel'
import BulkRenameModal, { BulkRenamePattern } from '../components/BulkRenameModal'
import toast from 'react-hot-toast'
import { uploadImages, batchAnalyzeImages, bulkRenameFiles } from '../services/api'

export default function ImageGallery() {
  const { images, addImages, removeImage, updateImage, selectedImageIds, clearSelection } = useApp()
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [viewingImage, setViewingImage] = useState<number | null>(null)
  const [showBulkRenameModal, setShowBulkRenameModal] = useState(false)

  const selectedImage = viewingImage !== null ? images.find(img => img.id === viewingImage) : null

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)

    try {
      const response = await uploadImages(files)

      const successfulUploads = response.results
        .filter(r => r.success)
        .map(r => ({
          id: r.id!,
          filename: r.filename,
          current_filename: r.filename,
          file_path: '',
          file_size: r.size || 0,
          mime_type: '',
          width: parseInt(r.dimensions?.split('x')[0] || '0'),
          height: parseInt(r.dimensions?.split('x')[1] || '0'),
        }))

      addImages(successfulUploads)

      toast.success(`Successfully uploaded ${response.succeeded} of ${response.total} images`)

      if (response.results.some(r => !r.success)) {
        const errors = response.results.filter(r => !r.success)
        errors.forEach(err => {
          toast.error(`Failed to upload ${err.filename}: ${err.error}`)
        })
      }

      // Reset file input
      e.target.value = ''
    } catch (error) {
      console.error('Upload error:', error)
      toast.error('Error uploading files. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const handleBatchAnalyze = async () => {
    const imagesToAnalyze = selectedImageIds.length > 0
      ? selectedImageIds
      : images.filter(img => !img.ai_description).map(img => img.id)

    if (imagesToAnalyze.length === 0) {
      toast.error('No images to analyze')
      return
    }

    setAnalyzing(true)

    try {
      toast.loading(`Analyzing ${imagesToAnalyze.length} images...`, { id: 'batch-analyze' })

      const response = await batchAnalyzeImages(imagesToAnalyze)

      response.results.forEach(result => {
        if (result.success && result.analysis) {
          updateImage(result.image_id, {
            ai_description: result.analysis.description,
            ai_tags: result.analysis.tags,
            ai_objects: result.analysis.objects,
            ai_scene: result.analysis.scene,
            analyzed_at: new Date().toISOString(),
          })
        }
      })

      toast.success(`Successfully analyzed ${response.succeeded} of ${response.total} images`, {
        id: 'batch-analyze',
      })

      if (selectedImageIds.length > 0) {
        clearSelection()
      }
    } catch (error) {
      console.error('Batch analysis error:', error)
      toast.error('Error analyzing images', { id: 'batch-analyze' })
    } finally {
      setAnalyzing(false)
    }
  }

  const handleBatchDelete = (imageIds: number[]) => {
    if (imageIds.length === 0) {
      toast.error('No images selected')
      return
    }

    if (confirm(`Delete ${imageIds.length} selected images?`)) {
      imageIds.forEach(id => removeImage(id))
      clearSelection()
      toast.success(`Deleted ${imageIds.length} images`)
    }
  }

  const handleBulkRename = async (pattern: BulkRenamePattern) => {
    const selectedImages = images.filter(img => selectedImageIds.includes(img.id))

    try {
      toast.loading(`Renaming ${selectedImages.length} images...`, { id: 'bulk-rename' })

      const response = await bulkRenameFiles(selectedImageIds, pattern)

      response.results.forEach((result) => {
        if (result.success && result.new_filename) {
          updateImage(result.image_id, {
            current_filename: result.new_filename,
            filename: result.new_filename,
          })
        }
      })

      toast.success(`Successfully renamed ${response.succeeded} of ${response.total} images`, {
        id: 'bulk-rename',
      })

      if (response.results.some((r) => !r.success)) {
        const errors = response.results.filter((r) => !r.success)
        errors.forEach((err) => {
          toast.error(`Failed to rename image ${err.image_id}: ${err.error}`)
        })
      }

      clearSelection()
    } catch (error) {
      console.error('Bulk rename error:', error)
      toast.error('Error renaming images', { id: 'bulk-rename' })
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Image Gallery</h1>
            <p className="text-gray-600 mt-1">
              {images.length} {images.length === 1 ? 'image' : 'images'}
              {selectedImageIds.length > 0 && ` · ${selectedImageIds.length} selected`}
            </p>
          </div>

          <div className="flex gap-3">
            {selectedImageIds.length > 0 && (
              <Button
                variant="secondary"
                icon={<Edit2 className="w-5 h-5" />}
                onClick={() => setShowBulkRenameModal(true)}
              >
                Bulk Rename ({selectedImageIds.length})
              </Button>
            )}

            {images.length > 0 && (
              <Button
                variant="primary"
                icon={<Sparkles className="w-5 h-5" />}
                onClick={handleBatchAnalyze}
                loading={analyzing}
                disabled={analyzing}
              >
                {selectedImageIds.length > 0 ? 'Analyze Selected' : 'Analyze All'}
              </Button>
            )}

            <label className="relative">
              <Button
                variant="primary"
                icon={<Upload className="w-5 h-5" />}
                disabled={uploading}
                loading={uploading}
              >
                Upload Images
              </Button>
              <input
                type="file"
                multiple
                accept="image/*,video/*"
                onChange={handleUpload}
                className="absolute inset-0 opacity-0 cursor-pointer"
                disabled={uploading}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Loading state */}
      {uploading && (
        <div className="mb-6">
          <LoadingSpinner text="Uploading images..." />
        </div>
      )}

      {/* Image Selection Panel with filters and sorting */}
      {images.length === 0 && !uploading ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg mb-2">No images uploaded yet</p>
          <p className="text-gray-500">
            Click "Upload Images" to get started with AI-powered analysis
          </p>
        </div>
      ) : (
        <ImageSelectionPanel
          onDeleteSelected={handleBatchDelete}
          showActions={true}
          enableFilters={true}
          enableSearch={true}
          enableSorting={true}
        />
      )}

      {/* Image details modal */}
      {selectedImage && (
        <Modal
          isOpen={!!selectedImage}
          onClose={() => setViewingImage(null)}
          title="Image Details"
          size="lg"
          footer={
            <Button variant="secondary" onClick={() => setViewingImage(null)}>
              Close
            </Button>
          }
        >
          <div className="space-y-4">
            <img
              src={`/api/images/${selectedImage.id}/thumbnail`}
              alt={selectedImage.current_filename}
              className="w-full rounded-lg"
            />

            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Filename</h3>
              <p className="text-gray-700">{selectedImage.current_filename}</p>
            </div>

            {selectedImage.ai_description && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">AI Description</h3>
                <p className="text-gray-700">{selectedImage.ai_description}</p>
              </div>
            )}

            {selectedImage.ai_tags && selectedImage.ai_tags.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedImage.ai_tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedImage.ai_scene && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Scene Type</h3>
                <p className="text-gray-700 capitalize">{selectedImage.ai_scene}</p>
              </div>
            )}

            {selectedImage.ai_objects && selectedImage.ai_objects.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Detected Objects</h3>
                <p className="text-gray-700">{selectedImage.ai_objects.join(', ')}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Dimensions</h3>
                <p className="text-gray-700">
                  {selectedImage.width}×{selectedImage.height}
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">File Size</h3>
                <p className="text-gray-700">
                  {(selectedImage.file_size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Bulk Rename Modal */}
      <BulkRenameModal
        isOpen={showBulkRenameModal}
        onClose={() => setShowBulkRenameModal(false)}
        images={images.filter(img => selectedImageIds.includes(img.id))}
        onApply={handleBulkRename}
      />
    </div>
  )
}
