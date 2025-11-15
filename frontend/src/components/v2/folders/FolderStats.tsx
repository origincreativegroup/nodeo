/**
 * Folder statistics dashboard component
 */

import { FolderOpen, FileCheck, Clock, AlertCircle } from 'lucide-react'
import type { FolderStats } from '../../../types/v2'

interface FolderStatsProps {
  stats: FolderStats | undefined
  isLoading?: boolean
}

export default function FolderStats({ stats, isLoading }: FolderStatsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (!stats) return null

  const statCards = [
    {
      label: 'Total Folders',
      value: stats.total_folders,
      subtext: `${stats.active_folders} active`,
      icon: FolderOpen,
      color: 'blue',
    },
    {
      label: 'Total Files',
      value: stats.total_files.toLocaleString(),
      subtext: `${stats.total_analyzed.toLocaleString()} analyzed`,
      icon: FileCheck,
      color: 'green',
    },
    {
      label: 'Pending Suggestions',
      value: stats.total_pending,
      subtext: 'awaiting review',
      icon: Clock,
      color: 'yellow',
    },
    {
      label: 'Scanning',
      value: stats.scanning_folders,
      subtext: `${stats.error_folders} errors`,
      icon: AlertCircle,
      color: stats.error_folders > 0 ? 'red' : 'purple',
    },
  ]

  const colorClasses = {
    blue: { bg: 'bg-blue-50', icon: 'text-blue-600', text: 'text-blue-900' },
    green: { bg: 'bg-green-50', icon: 'text-green-600', text: 'text-green-900' },
    yellow: { bg: 'bg-yellow-50', icon: 'text-yellow-600', text: 'text-yellow-900' },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-600', text: 'text-purple-900' },
    red: { bg: 'bg-red-50', icon: 'text-red-600', text: 'text-red-900' },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {statCards.map((stat, index) => {
        const colors = colorClasses[stat.color as keyof typeof colorClasses]
        const Icon = stat.icon

        return (
          <div
            key={index}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="text-sm font-medium text-gray-600">{stat.label}</div>
              <div className={`p-2 rounded-lg ${colors.bg}`}>
                <Icon className={`w-5 h-5 ${colors.icon}`} />
              </div>
            </div>
            <div className={`text-3xl font-bold ${colors.text} mb-1`}>{stat.value}</div>
            <div className="text-xs text-gray-500">{stat.subtext}</div>
          </div>
        )
      })}
    </div>
  )
}
