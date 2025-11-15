/**
 * Status indicator component for watched folders
 */

import type { WatchedFolderStatus } from '../../../types/v2'

interface StatusIndicatorProps {
  status: WatchedFolderStatus
  className?: string
}

export default function StatusIndicator({ status, className = '' }: StatusIndicatorProps) {
  const config = {
    active: {
      color: 'text-green-600',
      bg: 'bg-green-100',
      icon: '●',
      label: 'Active',
    },
    scanning: {
      color: 'text-blue-600',
      bg: 'bg-blue-100',
      icon: '◐',
      label: 'Scanning',
      animate: true,
    },
    paused: {
      color: 'text-yellow-600',
      bg: 'bg-yellow-100',
      icon: '❚❚',
      label: 'Paused',
    },
    error: {
      color: 'text-red-600',
      bg: 'bg-red-100',
      icon: '⚠',
      label: 'Error',
    },
  }

  const statusConfig = config[status]
  const { color, bg, icon, label } = statusConfig
  const animate = 'animate' in statusConfig ? statusConfig.animate : false

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full ${bg} ${className}`}>
      <span className={`${color} text-lg ${animate ? 'animate-pulse' : ''}`}>{icon}</span>
      <span className={`${color} font-medium text-sm`}>{label}</span>
    </div>
  )
}
