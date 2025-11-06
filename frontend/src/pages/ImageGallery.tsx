import { useState } from 'react'
import { Upload, Sparkles, Trash2, CheckSquare, Square } from 'lucide-react'
import { useApp } from '../context/AppContext'
import Button from '../components/Button'
import LoadingSpinner from '../components/LoadingSpinner'
import Modal from '../components/Modal'
import ImageCard from '../components/ImageCard'
import toast from 'react-hot-toast'
import { uploadImages, analyzeImage, batchAnalyzeImages } from '../services/api'

export default function ImageGallery() {
  const { images, addImages, removeImage, updateImage, selectedImageIds, toggleImageSelection, clearSelection, selectAll } = useApp()
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [viewingImage, setViewingImage] = useState<number | null>(null)

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

  const handleAnalyzeSingle = async (imageId: number) => {
    try {
      toast.loading(`Analyzing image...`, { id: `analyze-${imageId}` })

      const response = await analyzeImage(imageId)

      if (response.success) {
        updateImage(imageId, {
          ai_description: response.analysis.description,
          ai_tags: response.analysis.tags,
          ai_objects: response.analysis.objects,
          ai_scene: response.analysis.scene,
          analyzed_at: new Date().toISOString(),
        })

        toast.success('Analysis complete!', { id: `analyze-${imageId}` })
      }
    } catch (error) {
      console.error('Analysis error:', error)
      toast.error('Failed to analyze image', { id: `analyze-${imageId}` })
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

  const handleDelete = (imageId: number) => {
    if (confirm('Are you sure you want to delete this image?')) {
      removeImage(imageId)
      toast.success('Image deleted')
    }
  }

  const handleBatchDelete = () => {
    if (selectedImageIds.length === 0) {
      toast.error('No images selected')
      return
    }

    if (confirm(`Delete ${selectedImageIds.length} selected images?`)) {
      selectedImageIds.forEach(id => removeImage(id))
      clearSelection()
      toast.success(`Deleted ${selectedImageIds.length} images`)
    }
  }

  const allSelected = images.length > 0 && selectedImageIds.length === images.length

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Image Gallery</h1>
          <p className="text-gray-600 mt-1">
            {images.length} {images.length === 1 ? 'image' : 'images'}
            {selectedImageIds.length > 0 && ` · ${selectedImageIds.length} selected`}
          </p>
        </div>

        <div className="flex gap-3">
          {selectedImageIds.length > 0 && (
            <>
              <Button
                variant="danger"
                icon={<Trash2 className="w-5 h-5" />}
                onClick={handleBatchDelete}
              >
                Delete Selected
              </Button>
              <Button
                variant="secondary"
                onClick={clearSelection}
              >
                Clear Selection
              </Button>
            </>
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
              accept="image/*"
              onChange={handleUpload}
              className="absolute inset-0 opacity-0 cursor-pointer"
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {/* Batch actions bar */}
      {images.length > 0 && (
        <div className="mb-6 flex items-center gap-4 bg-white p-4 rounded-lg shadow">
          <button
            onClick={() => allSelected ? clearSelection() : selectAll()}
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
              {selectedImageIds.length} of {images.length} selected
            </span>
          )}
        </div>
      )}

      {/* Loading state */}
      {uploading && (
        <div className="mb-6">
          <LoadingSpinner text="Uploading images..." />
        </div>
      )}

      {/* Image grid */}
      {images.length === 0 && !uploading ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 text-lg mb-2">No images uploaded yet</p>
          <p className="text-gray-500">
            Click "Upload Images" to get started with AI-powered analysis
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {images.map(image => (
            <ImageCard
              key={image.id}
              image={image}
              isSelected={selectedImageIds.includes(image.id)}
              onSelect={() => toggleImageSelection(image.id)}
              onDelete={() => handleDelete(image.id)}
              onViewDetails={() => setViewingImage(image.id)}
              onAnalyze={() => handleAnalyzeSingle(image.id)}
            />
          ))}
        </div>
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
    </div>
  )
}
