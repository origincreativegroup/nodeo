import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Upload, ArrowLeft, Sparkles } from 'lucide-react'
import axios from 'axios'

interface ImageItem {
  id: number
  filename: string
  size: number
  dimensions: string
}

export default function ImageGallery() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)

    const formData = new FormData()
    Array.from(files).forEach(file => {
      formData.append('files', file)
    })

    try {
      const response = await axios.post('/api/images/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const uploaded = response.data.results
        .filter((r: any) => r.success)
        .map((r: any) => ({
          id: r.id,
          filename: r.filename,
          size: r.size,
          dimensions: r.dimensions,
        }))

      setImages([...images, ...uploaded])
    } catch (error) {
      console.error('Upload error:', error)
      alert('Error uploading files')
    } finally {
      setUploading(false)
    }
  }

  const handleBatchAnalyze = async () => {
    if (images.length === 0) return

    setAnalyzing(true)

    try {
      const imageIds = images.map(img => img.id)
      await axios.post('/api/images/batch-analyze', imageIds)

      alert('Batch analysis completed!')
    } catch (error) {
      console.error('Analysis error:', error)
      alert('Error analyzing images')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-blue-600 hover:text-blue-800">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-3xl font-bold">Image Gallery</h1>
          </div>

          <div className="flex gap-4">
            <label className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 cursor-pointer flex items-center gap-2">
              <Upload className="w-5 h-5" />
              {uploading ? 'Uploading...' : 'Upload Images'}
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>

            {images.length > 0 && (
              <button
                onClick={handleBatchAnalyze}
                disabled={analyzing}
                className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 flex items-center gap-2"
              >
                <Sparkles className="w-5 h-5" />
                {analyzing ? 'Analyzing...' : 'Analyze All'}
              </button>
            )}
          </div>
        </div>

        {images.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-lg shadow">
            <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 text-lg">No images uploaded yet</p>
            <p className="text-gray-500 mt-2">
              Click "Upload Images" to get started
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {images.map(img => (
              <div key={img.id} className="bg-white rounded-lg shadow p-4">
                <div className="aspect-square bg-gray-200 rounded mb-3 flex items-center justify-center">
                  <span className="text-gray-500">Image Preview</span>
                </div>
                <p className="font-semibold truncate">{img.filename}</p>
                <p className="text-sm text-gray-600">{img.dimensions}</p>
                <p className="text-sm text-gray-500">
                  {(img.size / 1024).toFixed(1)} KB
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
