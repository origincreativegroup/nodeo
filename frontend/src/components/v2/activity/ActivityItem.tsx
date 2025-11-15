/**
 * Activity item component - displays a single activity log entry in timeline format
 */

import { useState } from 'react'
import {
  FileText,
  Check,
  X,
  Scan,
  AlertCircle,
  FolderPlus,
  FolderMinus,
  Undo2,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import type { ActivityLog } from '../../../types/v2'

interface ActivityItemProps {
  activity: ActivityLog
  onRollback?: (activityId: string) => void
  isRollingBack?: boolean
}

export default function ActivityItem({ activity, onRollback, isRollingBack }: ActivityItemProps) {
  const [expanded, setExpanded] = useState(false)

  const getActionIcon = () => {
    switch (activity.action_type) {
      case 'rename':
        return FileText
      case 'approve':
        return Check
      case 'reject':
        return X
      case 'scan':
        return Scan
      case 'error':
        return AlertCircle
      case 'folder_added':
        return FolderPlus
      case 'folder_removed':
        return FolderMinus
      default:
        return FileText
    }
  }

  const getActionColor = () => {
    switch (activity.action_type) {
      case 'rename':
        return 'bg-blue-500'
      case 'approve':
        return 'bg-green-500'
      case 'reject':
        return 'bg-red-500'
      case 'scan':
        return 'bg-purple-500'
      case 'error':
        return 'bg-red-600'
      case 'folder_added':
        return 'bg-green-600'
      case 'folder_removed':
        return 'bg-orange-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusColor = () => {
    switch (activity.status) {
      case 'success':
        return 'text-green-600 bg-green-50'
      case 'failed':
        return 'text-red-600 bg-red-50'
      case 'pending':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'Just now'
  }

  const formatFullTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const Icon = getActionIcon()
  const canRollback = activity.action_type === 'rename' && activity.status === 'success'

  return (
    <div className="relative pl-8 pb-6">
      {/* Timeline line */}
      <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gray-200" />

      {/* Icon */}
      <div className={`absolute left-0 top-0 w-6 h-6 rounded-full ${getActionColor()} flex items-center justify-center`}>
        <Icon className="w-3 h-3 text-white" />
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-gray-900 capitalize">
                {activity.action_type.replace('_', ' ')}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor()}`}>
                {activity.status}
              </span>
              <span className="text-xs text-gray-500" title={formatFullTimestamp(activity.created_at)}>
                {formatTimestamp(activity.created_at)}
              </span>
            </div>

            {/* Details */}
            {activity.action_type === 'rename' && activity.original_filename && activity.new_filename && (
              <div className="space-y-1 mb-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">From:</span>
                  <span className="text-gray-900 font-medium truncate" title={activity.original_filename}>
                    {activity.original_filename}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500">To:</span>
                  <span className="text-blue-600 font-medium truncate" title={activity.new_filename}>
                    {activity.new_filename}
                  </span>
                </div>
              </div>
            )}

            {activity.action_type === 'folder_added' && activity.folder_path && (
              <p className="text-sm text-gray-600 mb-2">
                Added folder: <span className="font-medium text-gray-900">{activity.watched_folder_name}</span>
              </p>
            )}

            {activity.action_type === 'folder_removed' && (
              <p className="text-sm text-gray-600 mb-2">
                Removed folder: <span className="font-medium text-gray-900">{activity.watched_folder_name}</span>
              </p>
            )}

            {activity.action_type === 'scan' && (
              <p className="text-sm text-gray-600 mb-2">
                Scanned folder: <span className="font-medium text-gray-900">{activity.watched_folder_name}</span>
              </p>
            )}

            {/* Folder info */}
            {activity.watched_folder_name && activity.action_type === 'rename' && (
              <p className="text-xs text-gray-500 mb-2">
                📁 {activity.watched_folder_name}
              </p>
            )}

            {/* Error message */}
            {activity.error_message && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                <span className="font-medium">Error:</span> {activity.error_message}
              </div>
            )}

            {/* Metadata toggle */}
            {activity.metadata && Object.keys(activity.metadata).length > 0 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
              >
                {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {expanded ? 'Hide' : 'Show'} details
              </button>
            )}

            {/* Expanded metadata */}
            {expanded && activity.metadata && (
              <div className="mt-2 p-3 bg-gray-50 rounded text-xs">
                <pre className="text-gray-700 overflow-x-auto">
                  {JSON.stringify(activity.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Actions */}
          {canRollback && onRollback && (
            <button
              onClick={() => onRollback(activity.id)}
              disabled={isRollingBack}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Rollback this rename"
            >
              {isRollingBack ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Undo2 className="w-4 h-4" />
              )}
              Rollback
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
