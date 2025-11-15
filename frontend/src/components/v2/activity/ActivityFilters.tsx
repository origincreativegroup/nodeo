/**
 * Activity filters component - filter activity log entries
 */

import { Filter, ChevronDown } from 'lucide-react'
import type { WatchedFolder, ActivityActionType } from '../../../types/v2'

interface ActivityFiltersProps {
  folders: WatchedFolder[]
  selectedFolder: string
  selectedActionType: ActivityActionType | 'all'
  selectedStatus: string
  selectedDays: number
  onFolderChange: (folderId: string) => void
  onActionTypeChange: (actionType: ActivityActionType | 'all') => void
  onStatusChange: (status: string) => void
  onDaysChange: (days: number) => void
}

export default function ActivityFilters({
  folders,
  selectedFolder,
  selectedActionType,
  selectedStatus,
  selectedDays,
  onFolderChange,
  onActionTypeChange,
  onStatusChange,
  onDaysChange,
}: ActivityFiltersProps) {
  const actionTypes: Array<{ value: ActivityActionType | 'all'; label: string }> = [
    { value: 'all', label: 'All Actions' },
    { value: 'rename', label: 'Rename' },
    { value: 'approve', label: 'Approve' },
    { value: 'reject', label: 'Reject' },
    { value: 'scan', label: 'Scan' },
    { value: 'error', label: 'Error' },
    { value: 'folder_added', label: 'Folder Added' },
    { value: 'folder_removed', label: 'Folder Removed' },
  ]

  const statuses = [
    { value: 'all', label: 'All Status' },
    { value: 'success', label: 'Success' },
    { value: 'failed', label: 'Failed' },
    { value: 'pending', label: 'Pending' },
  ]

  const timeRanges = [
    { value: 1, label: 'Last 24 hours' },
    { value: 7, label: 'Last 7 days' },
    { value: 30, label: 'Last 30 days' },
    { value: 90, label: 'Last 90 days' },
  ]

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Time Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Time Range
          </label>
          <div className="relative">
            <select
              value={selectedDays}
              onChange={(e) => onDaysChange(parseInt(e.target.value))}
              className="w-full appearance-none px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
            >
              {timeRanges.map((range) => (
                <option key={range.value} value={range.value}>
                  {range.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

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
                  {folder.name}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Action Type Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Action Type
          </label>
          <div className="relative">
            <select
              value={selectedActionType}
              onChange={(e) => onActionTypeChange(e.target.value as ActivityActionType | 'all')}
              className="w-full appearance-none px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
            >
              {actionTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
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
              onChange={(e) => onStatusChange(e.target.value)}
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
      </div>
    </div>
  )
}
