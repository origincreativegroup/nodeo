/**
 * Activity Log - View and manage activity history
 */

import { useState } from 'react'
import { RefreshCw, Download, History, AlertCircle } from 'lucide-react'
import {
  useActivityLog,
  useActivityStats,
  useRollbackRename,
  useExportActivityLog,
} from '../../hooks/v2/useActivity'
import { useFolders } from '../../hooks/v2/useFolders'
import ActivityItem from '../../components/v2/activity/ActivityItem'
import ActivityFilters from '../../components/v2/activity/ActivityFilters'
import ActivityStats from '../../components/v2/activity/ActivityStats'
import type { ActivityActionType } from '../../types/v2'

export default function ActivityLog() {
  const [selectedFolder, setSelectedFolder] = useState('')
  const [selectedActionType, setSelectedActionType] = useState<ActivityActionType | 'all'>('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedDays, setSelectedDays] = useState(7)
  const [showExportMenu, setShowExportMenu] = useState(false)

  // Fetch data
  const { data: folders = [] } = useFolders()
  const { data: stats, isLoading: statsLoading } = useActivityStats(selectedDays)
  const { data: activities = [], isLoading, refetch } = useActivityLog({
    folder_id: selectedFolder || undefined,
    action_type: selectedActionType === 'all' ? undefined : selectedActionType,
    status: selectedStatus === 'all' ? undefined : selectedStatus,
    days: selectedDays,
  })

  // Mutations
  const rollbackRename = useRollbackRename()
  const exportLog = useExportActivityLog()

  // Handlers
  const handleRollback = (activityId: string) => {
    if (window.confirm('Are you sure you want to rollback this rename? The file will be restored to its original name.')) {
      rollbackRename.mutate(activityId)
    }
  }

  const handleExport = (format: 'csv' | 'json') => {
    exportLog.mutate({ format, days: selectedDays })
    setShowExportMenu(false)
  }

  const handleClearFilters = () => {
    setSelectedFolder('')
    setSelectedActionType('all')
    setSelectedStatus('all')
    setSelectedDays(7)
  }

  const hasFilters = selectedFolder || selectedActionType !== 'all' || selectedStatus !== 'all' || selectedDays !== 7

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                <History className="w-8 h-8 text-gray-700" />
                Activity Log
              </h1>
              <p className="text-gray-600 mt-1">
                Track all rename operations, approvals, and system activities
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => refetch()}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>

              {/* Export Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  disabled={exportLog.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {exportLog.isPending ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Export
                </button>
                {showExportMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                    <button
                      onClick={() => handleExport('csv')}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as CSV
                    </button>
                    <button
                      onClick={() => handleExport('json')}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as JSON
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="mb-6">
          <ActivityStats stats={stats} isLoading={statsLoading} />
        </div>

        {/* Filters */}
        <div className="mb-6">
          <ActivityFilters
            folders={folders}
            selectedFolder={selectedFolder}
            selectedActionType={selectedActionType}
            selectedStatus={selectedStatus}
            selectedDays={selectedDays}
            onFolderChange={setSelectedFolder}
            onActionTypeChange={setSelectedActionType}
            onStatusChange={setSelectedStatus}
            onDaysChange={setSelectedDays}
          />
        </div>

        {/* Active Filters Indicator */}
        {hasFilters && (
          <div className="mb-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-700">
              Filters active - showing {activities.length} result{activities.length !== 1 ? 's' : ''}
            </p>
            <button
              onClick={handleClearFilters}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Clear all filters
            </button>
          </div>
        )}

        {/* Timeline */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Timeline</h2>

          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="relative pl-8 pb-6 animate-pulse">
                  <div className="absolute left-0 top-0 w-6 h-6 bg-gray-200 rounded-full" />
                  <div className="bg-gray-100 rounded-lg p-4">
                    <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : activities.length > 0 ? (
            <div className="space-y-0">
              {activities.map((activity) => (
                <ActivityItem
                  key={activity.id}
                  activity={activity}
                  onRollback={handleRollback}
                  isRollingBack={rollbackRename.isPending}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No activity found
              </h3>
              <p className="text-gray-600 mb-4">
                {hasFilters
                  ? 'No activities match your current filters.'
                  : 'No activities recorded yet. Start adding folders to begin monitoring.'}
              </p>
              {hasFilters && (
                <button
                  onClick={handleClearFilters}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>

        {/* Info */}
        {activities.length > 0 && (
          <div className="mt-4 text-center text-sm text-gray-500">
            Showing {activities.length} activit{activities.length !== 1 ? 'ies' : 'y'} from the last {selectedDays} day{selectedDays !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Click outside to close export menu */}
      {showExportMenu && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setShowExportMenu(false)}
        />
      )}
    </div>
  )
}
