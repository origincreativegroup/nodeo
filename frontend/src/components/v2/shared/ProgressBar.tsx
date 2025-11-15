/**
 * Progress bar component with real-time updates
 */

import type { WatchedFolderStatus } from '../../../types/v2'

interface ProgressBarProps {
  current: number
  total: number
  status?: WatchedFolderStatus
  className?: string
}

export default function ProgressBar({ current, total, status, className = '' }: ProgressBarProps) {
  const progress = total > 0 ? Math.round((current / total) * 100) : 0

  const getColorClass = () => {
    if (status === 'scanning') return 'bg-blue-500'
    if (status === 'error') return 'bg-red-500'
    if (status === 'paused') return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getProgressText = () => {
    if (status === 'scanning') return 'Scanning...'
    if (status === 'error') return 'Error'
    if (status === 'paused') return 'Paused'
    return 'Complete'
  }

  return (
    <div className={`w-full ${className}`}>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{getProgressText()}</span>
        <span className="font-medium text-gray-900">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${getColorClass()}`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <div className="text-xs text-gray-500 mt-1">
        {current.toLocaleString()} / {total.toLocaleString()} files analyzed
      </div>
    </div>
  )
}
