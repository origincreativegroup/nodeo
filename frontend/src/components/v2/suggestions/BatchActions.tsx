/**
 * Batch actions toolbar for suggestions
 */

import { Check, X, Play } from 'lucide-react'

interface BatchActionsProps {
  selectedCount: number
  totalCount: number
  onSelectAll: () => void
  onDeselectAll: () => void
  onBatchApprove: () => void
  onBatchReject: () => void
  onBatchExecute: () => void
  isExecuting?: boolean
}

export default function BatchActions({
  selectedCount,
  totalCount,
  onSelectAll,
  onDeselectAll,
  onBatchApprove,
  onBatchReject,
  onBatchExecute,
  isExecuting = false,
}: BatchActionsProps) {
  if (totalCount === 0) return null

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Selection Info */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedCount === totalCount && totalCount > 0}
              onChange={() => {
                if (selectedCount === totalCount) {
                  onDeselectAll()
                } else {
                  onSelectAll()
                }
              }}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">
              {selectedCount > 0 ? (
                <>
                  <span className="text-blue-600">{selectedCount}</span> selected
                </>
              ) : (
                'Select all'
              )}
            </span>
          </div>

          {selectedCount > 0 && (
            <button
              onClick={onDeselectAll}
              className="text-sm text-gray-600 hover:text-gray-900 underline"
            >
              Clear selection
            </button>
          )}
        </div>

        {/* Batch Actions */}
        {selectedCount > 0 && (
          <div className="flex items-center gap-2">
            <button
              onClick={onBatchApprove}
              disabled={isExecuting}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Check className="w-4 h-4" />
              Approve ({selectedCount})
            </button>

            <button
              onClick={onBatchReject}
              disabled={isExecuting}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <X className="w-4 h-4" />
              Reject ({selectedCount})
            </button>

            <button
              onClick={onBatchExecute}
              disabled={isExecuting}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isExecuting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Execute ({selectedCount})
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
