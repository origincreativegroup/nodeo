import { Filter, X } from 'lucide-react'
import { ImageFilterOptions } from '../hooks/useImageFilter'

interface ImageFiltersProps {
  options: ImageFilterOptions
  onChange: (options: ImageFilterOptions) => void
  stats: {
    total: number
    filtered: number
    analyzed: number
    unanalyzed: number
    imageCount: number
    videoCount: number
  }
}

export default function ImageFilters({ options, onChange, stats }: ImageFiltersProps) {
  const hasActiveFilters =
    options.analysisStatus !== 'all' ||
    options.mediaType !== 'all' ||
    options.minFileSize !== undefined ||
    options.maxFileSize !== undefined ||
    options.minWidth !== undefined ||
    options.minHeight !== undefined ||
    (options.tags && options.tags.length > 0)

  const clearFilters = () => {
    onChange({
      ...options,
      analysisStatus: 'all',
      mediaType: 'all',
      minFileSize: undefined,
      maxFileSize: undefined,
      minWidth: undefined,
      minHeight: undefined,
      tags: undefined,
    })
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
          <Filter className="w-4 h-4 text-blue-600" />
          Filters
        </h3>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
          >
            <X className="w-3 h-3" />
            Clear all
          </button>
        )}
      </div>

      <div className="text-xs text-gray-600">
        Showing {stats.filtered} of {stats.total} files
      </div>

      <div className="space-y-3">
        {/* Analysis Status Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Analysis Status
          </label>
          <select
            value={options.analysisStatus}
            onChange={(e) =>
              onChange({
                ...options,
                analysisStatus: e.target.value as ImageFilterOptions['analysisStatus'],
              })
            }
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All ({stats.total})</option>
            <option value="analyzed">Analyzed ({stats.analyzed})</option>
            <option value="unanalyzed">Unanalyzed ({stats.unanalyzed})</option>
          </select>
        </div>

        {/* Media Type Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Media Type</label>
          <select
            value={options.mediaType}
            onChange={(e) =>
              onChange({
                ...options,
                mediaType: e.target.value as ImageFilterOptions['mediaType'],
              })
            }
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Media</option>
            <option value="image">Images ({stats.imageCount})</option>
            <option value="video">Videos ({stats.videoCount})</option>
          </select>
        </div>

        {/* File Size Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            File Size (MB)
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Min"
              value={options.minFileSize || ''}
              onChange={(e) =>
                onChange({
                  ...options,
                  minFileSize: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="0"
              step="0.1"
            />
            <input
              type="number"
              placeholder="Max"
              value={options.maxFileSize || ''}
              onChange={(e) =>
                onChange({
                  ...options,
                  maxFileSize: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="0"
              step="0.1"
            />
          </div>
        </div>

        {/* Dimensions Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Minimum Dimensions (px)
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Width"
              value={options.minWidth || ''}
              onChange={(e) =>
                onChange({
                  ...options,
                  minWidth: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="0"
            />
            <input
              type="number"
              placeholder="Height"
              value={options.minHeight || ''}
              onChange={(e) =>
                onChange({
                  ...options,
                  minHeight: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="0"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
