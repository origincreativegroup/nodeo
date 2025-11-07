import { useState, useCallback, useMemo, useEffect } from 'react'
import { Grid3x3, List, CheckSquare, Square, Trash2, Edit2 } from 'lucide-react'
import { useApp, ImageData } from '../context/AppContext'
import { useImageFilter, defaultFilterOptions, ImageFilterOptions } from '../hooks/useImageFilter'
import ImageFilters from './ImageFilters'
import ImageSorting from './ImageSorting'
import ImageSearch from './ImageSearch'
import ImageCardUnified from './ImageCardUnified'
import Button from './Button'

type ViewMode = 'grid' | 'list'

interface ImageSelectionPanelProps {
  images?: ImageData[]
  onRenameSelected?: (imageIds: number[]) => void
  onDeleteSelected?: (imageIds: number[]) => void
  showActions?: boolean
  enableFilters?: boolean
  enableSearch?: boolean
  enableSorting?: boolean
  className?: string
}

export default function ImageSelectionPanel({
  images: externalImages,
  onRenameSelected,
  onDeleteSelected,
  showActions = true,
  enableFilters = true,
  enableSearch = true,
  enableSorting = true,
  className = '',
}: ImageSelectionPanelProps) {
  const { images: contextImages, selectedImageIds, toggleImageSelection, selectAll, clearSelection } = useApp()
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [filterOptions, setFilterOptions] = useState<ImageFilterOptions>(defaultFilterOptions)

  // Use external images if provided, otherwise use context images
  const sourceImages = externalImages || contextImages

  const { filteredImages, stats } = useImageFilter(sourceImages, filterOptions)

  const selectedCount = useMemo(() => {
    const filteredIds = new Set(filteredImages.map((img) => img.id))
    return selectedImageIds.filter((id) => filteredIds.has(id)).length
  }, [selectedImageIds, filteredImages])

  const allSelected = useMemo(() => {
    if (filteredImages.length === 0) return false
    return filteredImages.every((img) => selectedImageIds.includes(img.id))
  }, [filteredImages, selectedImageIds])

  const handleToggleSelectAll = useCallback(() => {
    if (allSelected) {
      clearSelection()
    } else {
      selectAll(filteredImages.map((img) => img.id))
    }
  }, [allSelected, clearSelection, selectAll, filteredImages])

  const handleSearchChange = useCallback(
    (query: string) => {
      setFilterOptions((prev) => ({ ...prev, searchQuery: query }))
    },
    []
  )

  const handleRenameClick = useCallback(() => {
    if (selectedCount > 0 && onRenameSelected) {
      onRenameSelected(selectedImageIds)
    }
  }, [selectedCount, selectedImageIds, onRenameSelected])

  const handleDeleteClick = useCallback(() => {
    if (selectedCount > 0 && onDeleteSelected) {
      if (confirm(`Delete ${selectedCount} selected images?`)) {
        onDeleteSelected(selectedImageIds)
      }
    }
  }, [selectedCount, selectedImageIds, onDeleteSelected])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + A: Select all
      if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
        e.preventDefault()
        if (filteredImages.length > 0) {
          selectAll(filteredImages.map((img) => img.id))
        }
      }

      // Escape: Clear selection
      if (e.key === 'Escape') {
        if (selectedImageIds.length > 0) {
          clearSelection()
        }
      }

      // Delete: Delete selected
      if (e.key === 'Delete' && selectedCount > 0 && onDeleteSelected) {
        handleDeleteClick()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [filteredImages, selectedImageIds, selectedCount, selectAll, clearSelection, onDeleteSelected, handleDeleteClick])

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search Bar */}
      {enableSearch && (
        <div className="bg-white rounded-lg shadow p-4">
          <ImageSearch
            value={filterOptions.searchQuery}
            onChange={handleSearchChange}
          />
        </div>
      )}

      {/* Toolbar */}
      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* Select All */}
          <button
            onClick={handleToggleSelectAll}
            className="flex items-center gap-2 text-gray-700 hover:text-gray-900"
            disabled={filteredImages.length === 0}
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

          {selectedCount > 0 && (
            <span className="text-sm text-gray-600">
              {selectedCount} of {filteredImages.length} selected
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Action Buttons */}
          {showActions && selectedCount > 0 && (
            <>
              {onRenameSelected && (
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Edit2 className="w-4 h-4" />}
                  onClick={handleRenameClick}
                >
                  Rename ({selectedCount})
                </Button>
              )}
              {onDeleteSelected && (
                <Button
                  variant="danger"
                  size="sm"
                  icon={<Trash2 className="w-4 h-4" />}
                  onClick={handleDeleteClick}
                >
                  Delete ({selectedCount})
                </Button>
              )}
            </>
          )}

          {/* Sorting */}
          {enableSorting && (
            <ImageSorting options={filterOptions} onChange={setFilterOptions} />
          )}

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 border border-gray-300 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded ${
                viewMode === 'grid'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              title="Grid view"
            >
              <Grid3x3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded ${
                viewMode === 'list'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px,1fr]">
        {/* Filters Sidebar */}
        {enableFilters && (
          <aside>
            <ImageFilters
              options={filterOptions}
              onChange={setFilterOptions}
              stats={stats}
            />
          </aside>
        )}

        {/* Image Grid/List */}
        <div className={enableFilters ? '' : 'col-span-full'}>
          {filteredImages.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <p className="text-gray-500">No images match your filters</p>
            </div>
          ) : (
            <div
              className={
                viewMode === 'grid'
                  ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
                  : 'space-y-2'
              }
            >
              {filteredImages.map((image) => (
                <ImageCardUnified
                  key={image.id}
                  image={image}
                  variant={viewMode}
                  selected={selectedImageIds.includes(image.id)}
                  onSelect={toggleImageSelection}
                  showActions={showActions}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
