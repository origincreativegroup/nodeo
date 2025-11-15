/**
 * Activity statistics component - displays activity stats dashboard
 */

import { Activity, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react'
import type { ActivityStats as ActivityStatsType } from '../../../types/v2'

interface ActivityStatsProps {
  stats: ActivityStatsType | undefined
  isLoading: boolean
}

export default function ActivityStats({ stats, isLoading }: ActivityStatsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Total Activities */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Total Activities</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_activities}</p>
            <p className="text-xs text-gray-500 mt-1">Last {stats.period_days} days</p>
          </div>
          <Activity className="w-8 h-8 text-gray-400" />
        </div>
      </div>

      {/* Success Rate */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Success Rate</p>
            <p className="text-2xl font-bold text-green-600">
              {Math.round(stats.success_rate * 100)}%
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {stats.by_status.success || 0} successful
            </p>
          </div>
          <TrendingUp className="w-8 h-8 text-green-400" />
        </div>
      </div>

      {/* Renames */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Renames</p>
            <p className="text-2xl font-bold text-blue-600">
              {stats.by_action.rename || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">Files renamed</p>
          </div>
          <CheckCircle className="w-8 h-8 text-blue-400" />
        </div>
      </div>

      {/* Errors */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Errors</p>
            <p className="text-2xl font-bold text-red-600">
              {(stats.by_status.failed || 0) + (stats.by_action.error || 0)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Failed operations</p>
          </div>
          <AlertCircle className="w-8 h-8 text-red-400" />
        </div>
      </div>
    </div>
  )
}
