/**
 * Folder card component displaying watched folder details
 */

import { FolderOpen, Pause, Play, RotateCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { WatchedFolder } from '../../../types/v2'
import ProgressBar from '../shared/ProgressBar'
import StatusIndicator from '../shared/StatusIndicator'

interface FolderCardProps {
  folder: WatchedFolder
  onPause: (folderId: string) => void
  onResume: (folderId: string) => void
  onRescan: (folderId: string) => void
  onDelete: (folderId: string) => void
}

export default function FolderCard({
  folder,
  onPause,
  onResume,
  onRescan,
  onDelete,
}: FolderCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const handleDelete = () => {
    if (showDeleteConfirm) {
      onDelete(folder.id)
      setShowDeleteConfirm(false)
    } else {
      setShowDeleteConfirm(true)
      setTimeout(() => setShowDeleteConfirm(false), 3000)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="p-2 bg-blue-50 rounded-lg">
            <FolderOpen className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">{folder.name}</h3>
            <p className="text-sm text-gray-500 truncate" title={folder.path}>
              {folder.path}
            </p>
          </div>
        </div>
        <StatusIndicator status={folder.status} />
      </div>

      {/* Progress */}
      <ProgressBar
        current={folder.analyzed_count}
        total={folder.file_count}
        status={folder.status}
        className="mb-4"
      />

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs text-gray-500">Files</div>
          <div className="text-lg font-semibold text-gray-900">{folder.file_count}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Analyzed</div>
          <div className="text-lg font-semibold text-green-600">{folder.analyzed_count}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Pending</div>
          <div className="text-lg font-semibold text-blue-600">{folder.pending_count}</div>
        </div>
      </div>

      {/* Last Scan */}
      <div className="text-xs text-gray-500 mb-4">
        Last scan: {formatDate(folder.last_scan_at)}
      </div>

      {/* Error Message */}
      {folder.error_message && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{folder.error_message}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {folder.status === 'active' || folder.status === 'scanning' ? (
          <button
            onClick={() => onPause(folder.id)}
            disabled={folder.status === 'scanning'}
            className="flex items-center gap-2 px-3 py-2 bg-yellow-50 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Pause className="w-4 h-4" />
            <span className="text-sm font-medium">Pause</span>
          </button>
        ) : (
          <button
            onClick={() => onResume(folder.id)}
            disabled={folder.status === 'error'}
            className="flex items-center gap-2 px-3 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            <span className="text-sm font-medium">Resume</span>
          </button>
        )}

        <button
          onClick={() => onRescan(folder.id)}
          disabled={folder.status === 'scanning'}
          className="flex items-center gap-2 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RotateCw className="w-4 h-4" />
          <span className="text-sm font-medium">Rescan</span>
        </button>

        <button
          onClick={handleDelete}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ml-auto ${
            showDeleteConfirm
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-red-50 text-red-700 hover:bg-red-100'
          }`}
        >
          <Trash2 className="w-4 h-4" />
          <span className="text-sm font-medium">
            {showDeleteConfirm ? 'Click to Confirm' : 'Remove'}
          </span>
        </button>
      </div>
    </div>
  )
}
