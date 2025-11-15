/**
 * Suggestion filters component - filter and sort suggestions
 */

import { Filter, ChevronDown } from 'lucide-react'
import type { WatchedFolder, SuggestionStatus } from '../../../types/v2'

interface SuggestionFiltersProps {
  folders: WatchedFolder[]
  selectedFolder: string
  selectedStatus: SuggestionStatus | 'all'
  minConfidence: number
  onFolderChange: (folderId: string) => void
  onStatusChange: (status: SuggestionStatus | 'all') => void
  onConfidenceChange: (confidence: number) => void
}

export default function SuggestionFilters({
  folders,
  selectedFolder,
  selectedStatus,
  minConfidence,
  onFolderChange,
  onStatusChange,
  onConfidenceChange,
}: SuggestionFiltersProps) {
  const statuses: Array<{ value: SuggestionStatus | 'all'; label: string }> = [
    { value: 'all', label: 'All Status' },
    { value: 'pending', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'applied', label: 'Applied' },
    { value: 'failed', label: 'Failed' },
  ]

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Folder Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Folder
          </label>
          <div className="relative">
            <select
              value={selectedFolder}
              onChange={(e) => onFolderChange(e.target.value)}
              className="w-full appearance-none px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
            >
              <option value="">All Folders</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name} ({folder.pending_count})
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Status
          </label>
          <div className="relative">
            <select
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value as SuggestionStatus | 'all')}
              className="w-full appearance-none px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
            >
              {statuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Confidence Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min Confidence: {Math.round(minConfidence * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={Math.round(minConfidence * 100)}
            onChange={(e) => onConfidenceChange(parseInt(e.target.value) / 100)}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
