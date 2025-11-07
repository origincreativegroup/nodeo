import { Search, X } from 'lucide-react'
import { useState, useEffect } from 'react'

interface ImageSearchProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export default function ImageSearch({
  value,
  onChange,
  placeholder = 'Search by filename, tags, description...',
  className = '',
}: ImageSearchProps) {
  const [localValue, setLocalValue] = useState(value)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(localValue)
    }, 300)

    return () => clearTimeout(timer)
  }, [localValue, onChange])

  // Sync with external value changes
  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleClear = () => {
    setLocalValue('')
    onChange('')
  }

  return (
    <div className={`relative ${className}`}>
      <div className="absolute left-3 top-1/2 -translate-y-1/2">
        <Search className="w-4 h-4 text-gray-400" />
      </div>
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
      {localValue && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-100 rounded"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>
      )}
    </div>
  )
}
