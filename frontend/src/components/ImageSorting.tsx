import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { ImageFilterOptions } from '../hooks/useImageFilter'

interface ImageSortingProps {
  options: ImageFilterOptions
  onChange: (options: ImageFilterOptions) => void
}

export default function ImageSorting({ options, onChange }: ImageSortingProps) {
  const sortOptions: Array<{ value: ImageFilterOptions['sortBy']; label: string }> = [
    { value: 'name', label: 'Name' },
    { value: 'date', label: 'Date' },
    { value: 'size', label: 'File Size' },
    { value: 'dimensions', label: 'Dimensions' },
  ]

  const toggleSortOrder = () => {
    onChange({
      ...options,
      sortOrder: options.sortOrder === 'asc' ? 'desc' : 'asc',
    })
  }

  return (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="w-4 h-4 text-gray-500" />
      <span className="text-sm font-medium text-gray-700">Sort by:</span>

      <select
        value={options.sortBy}
        onChange={(e) =>
          onChange({
            ...options,
            sortBy: e.target.value as ImageFilterOptions['sortBy'],
          })
        }
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        {sortOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <button
        onClick={toggleSortOrder}
        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
        title={options.sortOrder === 'asc' ? 'Ascending' : 'Descending'}
      >
        {options.sortOrder === 'asc' ? (
          <ArrowUp className="w-4 h-4 text-gray-600" />
        ) : (
          <ArrowDown className="w-4 h-4 text-gray-600" />
        )}
      </button>
    </div>
  )
}
