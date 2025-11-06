import { Check, Trash2, Sparkles, Eye } from 'lucide-react'
import { ImageData } from '../context/AppContext'
import Button from './Button'

interface ImageCardProps {
  image: ImageData
  isSelected: boolean
  onSelect: () => void
  onDelete: () => void
  onViewDetails: () => void
  onAnalyze: () => void
}

export default function ImageCard({
  image,
  isSelected,
  onSelect,
  onDelete,
  onViewDetails,
  onAnalyze,
}: ImageCardProps) {
  const hasAnalysis = !!image.ai_description

  return (
    <div className={`bg-white rounded-lg shadow hover:shadow-lg transition-shadow border-2 ${
      isSelected ? 'border-blue-500' : 'border-transparent'
    }`}>
      {/* Image preview */}
      <div className="relative aspect-square bg-gray-100 rounded-t-lg overflow-hidden group">
        <img
          src={`/api/images/${image.id}/thumbnail`}
          alt={image.current_filename}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.currentTarget.src = `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400" fill="%23e5e7eb"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%239ca3af" font-family="Arial" font-size="16">No preview</text></svg>`
          }}
        />

        {/* Checkbox overlay */}
        <div className="absolute top-2 left-2">
          <button
            onClick={onSelect}
            className={`w-6 h-6 rounded border-2 transition-colors ${
              isSelected
                ? 'bg-blue-600 border-blue-600'
                : 'bg-white border-gray-300 hover:border-blue-400'
            }`}
          >
            {isSelected && <Check className="w-4 h-4 text-white m-auto" />}
          </button>
        </div>

        {/* Quick actions */}
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            size="sm"
            variant="secondary"
            onClick={onViewDetails}
            className="!p-2"
          >
            <Eye className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="danger"
            onClick={onDelete}
            className="!p-2"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>

        {/* Analysis badge */}
        {hasAnalysis && (
          <div className="absolute bottom-2 right-2">
            <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              Analyzed
            </span>
          </div>
        )}
      </div>

      {/* Card content */}
      <div className="p-3">
        <h3 className="font-medium text-sm text-gray-900 truncate mb-1">
          {image.current_filename}
        </h3>

        {hasAnalysis ? (
          <p className="text-xs text-gray-600 line-clamp-2 mb-2">
            {image.ai_description}
          </p>
        ) : (
          <div className="mb-2">
            <Button
              size="sm"
              variant="primary"
              onClick={onAnalyze}
              icon={<Sparkles className="w-3 h-3" />}
              className="text-xs !py-1"
            >
              Analyze with AI
            </Button>
          </div>
        )}

        {image.ai_tags && image.ai_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {image.ai_tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
            {image.ai_tags.length > 3 && (
              <span className="text-xs text-gray-500">
                +{image.ai_tags.length - 3}
              </span>
            )}
          </div>
        )}

        <div className="text-xs text-gray-500">
          {image.width && image.height && (
            <span className="mr-2">
              {image.width}×{image.height}
            </span>
          )}
          {image.file_size && (
            <span>{(image.file_size / 1024).toFixed(1)} KB</span>
          )}
        </div>
      </div>
    </div>
  )
}
