/**
 * Suggestions Queue - View and manage rename suggestions
 */

import { useState } from 'react'
import { RefreshCw, Sparkles, CheckCircle, XCircle, Clock } from 'lucide-react'
import {
  useSuggestions,
  useSuggestionsStats,
  useUpdateSuggestion,
  useApproveSuggestion,
  useRejectSuggestion,
  useBatchApproveSuggestions,
  useBatchRejectSuggestions,
  useBatchExecuteSuggestions,
} from '../../hooks/v2/useSuggestions'
import { useFolders } from '../../hooks/v2/useFolders'
import SuggestionCard from '../../components/v2/suggestions/SuggestionCard'
import SuggestionFilters from '../../components/v2/suggestions/SuggestionFilters'
import BatchActions from '../../components/v2/suggestions/BatchActions'
import type { SuggestionStatus } from '../../types/v2'

export default function SuggestionsQueue() {
  const [selectedFolder, setSelectedFolder] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<SuggestionStatus | 'all'>('pending')
  const [minConfidence, setMinConfidence] = useState(0.0)
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set())

  // Fetch data
  const { data: folders = [] } = useFolders()
  const { data: stats, isLoading: statsLoading } = useSuggestionsStats()
  const { data: suggestions = [], isLoading, refetch } = useSuggestions({
    folder_id: selectedFolder || undefined,
    status: selectedStatus === 'all' ? undefined : selectedStatus,
    min_confidence: minConfidence,
  })

  // Mutations
  const updateSuggestion = useUpdateSuggestion()
  const approveSuggestion = useApproveSuggestion()
  const rejectSuggestion = useRejectSuggestion()
  const batchApprove = useBatchApproveSuggestions()
  const batchReject = useBatchRejectSuggestions()
  const batchExecute = useBatchExecuteSuggestions()

  // Selection handlers
  const handleSelectSuggestion = (id: string) => {
    const newSelection = new Set(selectedSuggestions)
    if (newSelection.has(id)) {
      newSelection.delete(id)
    } else {
      newSelection.add(id)
    }
    setSelectedSuggestions(newSelection)
  }

  const handleSelectAll = () => {
    setSelectedSuggestions(new Set(suggestions.map((s) => s.id)))
  }

  const handleDeselectAll = () => {
    setSelectedSuggestions(new Set())
  }

  // Action handlers
  const handleApprove = (id: string) => {
    approveSuggestion.mutate(id)
    setSelectedSuggestions((prev) => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }

  const handleReject = (id: string) => {
    rejectSuggestion.mutate(id)
    setSelectedSuggestions((prev) => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }

  const handleUpdate = (id: string, filename: string) => {
    updateSuggestion.mutate({ suggestionId: id, filename })
  }

  const handleBatchApprove = () => {
    batchApprove.mutate(Array.from(selectedSuggestions), {
      onSuccess: () => setSelectedSuggestions(new Set()),
    })
  }

  const handleBatchReject = () => {
    batchReject.mutate(Array.from(selectedSuggestions), {
      onSuccess: () => setSelectedSuggestions(new Set()),
    })
  }

  const handleBatchExecute = () => {
    if (
      !window.confirm(
        `Execute ${selectedSuggestions.size} approved renames? This will rename the files.`
      )
    ) {
      return
    }

    batchExecute.mutate(
      { suggestionIds: Array.from(selectedSuggestions), createBackups: true },
      {
        onSuccess: () => setSelectedSuggestions(new Set()),
      }
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                <Sparkles className="w-8 h-8 text-yellow-500" />
                Rename Suggestions
              </h1>
              <p className="text-gray-600 mt-1">
                Review AI-generated rename suggestions and approve changes
              </p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && !statsLoading && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                </div>
                <Sparkles className="w-8 h-8 text-gray-400" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Pending</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.pending}</p>
                </div>
                <Clock className="w-8 h-8 text-yellow-400" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Approved</p>
                  <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Rejected</p>
                  <p className="text-2xl font-bold text-red-600">{stats.rejected}</p>
                </div>
                <XCircle className="w-8 h-8 text-red-400" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Avg Confidence</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {Math.round(stats.average_confidence * 100)}%
                  </p>
                </div>
                <Sparkles className="w-8 h-8 text-blue-400" />
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6">
          <SuggestionFilters
            folders={folders}
            selectedFolder={selectedFolder}
            selectedStatus={selectedStatus}
            minConfidence={minConfidence}
            onFolderChange={setSelectedFolder}
            onStatusChange={setSelectedStatus}
            onConfidenceChange={setMinConfidence}
          />
        </div>

        {/* Batch Actions */}
        <div className="mb-6">
          <BatchActions
            selectedCount={selectedSuggestions.size}
            totalCount={suggestions.length}
            onSelectAll={handleSelectAll}
            onDeselectAll={handleDeselectAll}
            onBatchApprove={handleBatchApprove}
            onBatchReject={handleBatchReject}
            onBatchExecute={handleBatchExecute}
            isExecuting={batchExecute.isPending}
          />
        </div>

        {/* Suggestions Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 animate-pulse">
                <div className="aspect-square bg-gray-200 rounded-t-lg"></div>
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-full"></div>
                  <div className="h-8 bg-gray-200 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : suggestions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                selected={selectedSuggestions.has(suggestion.id)}
                onSelect={handleSelectSuggestion}
                onApprove={handleApprove}
                onReject={handleReject}
                onUpdate={handleUpdate}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-12 text-center">
            <div className="max-w-md mx-auto">
              <Sparkles className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No suggestions found
              </h3>
              <p className="text-gray-600 mb-4">
                {selectedStatus !== 'all' || selectedFolder || minConfidence > 0
                  ? 'Try adjusting your filters to see more suggestions.'
                  : 'Add folders to start monitoring and generate rename suggestions automatically.'}
              </p>
              {(selectedStatus !== 'all' || selectedFolder || minConfidence > 0) && (
                <button
                  onClick={() => {
                    setSelectedFolder('')
                    setSelectedStatus('all')
                    setMinConfidence(0)
                  }}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
