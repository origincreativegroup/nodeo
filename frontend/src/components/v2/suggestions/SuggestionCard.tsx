/**
 * Suggestion card component - displays a rename suggestion with image preview
 */

import { useState } from 'react'
import { Check, X, Edit2, Eye, Sparkles } from 'lucide-react'
import type { RenameSuggestion } from '../../../types/v2'

interface SuggestionCardProps {
  suggestion: RenameSuggestion
  selected: boolean
  onSelect: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  onUpdate: (id: string, filename: string) => void
}

export default function SuggestionCard({
  suggestion,
  selected,
  onSelect,
  onApprove,
  onReject,
  onUpdate,
}: SuggestionCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedFilename, setEditedFilename] = useState(suggestion.suggested_filename)

  const handleSaveEdit = () => {
    if (editedFilename.trim() && editedFilename !== suggestion.suggested_filename) {
      onUpdate(suggestion.id, editedFilename.trim())
    }
    setIsEditing(false)
  }

  const handleCancelEdit = () => {
    setEditedFilename(suggestion.suggested_filename)
    setIsEditing(false)
  }

  const getStatusColor = () => {
    switch (suggestion.status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      case 'applied':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getConfidenceColor = (score: number | null) => {
    if (!score) return 'text-gray-400'
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-orange-600'
  }

  const imageThumbnail = suggestion.asset_id
    ? `/api/storage/thumbnail/${suggestion.asset_id}`
    : null

  return (
    <div
      className={`bg-white rounded-lg border-2 transition-all ${
        selected ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      {/* Image Preview */}
      <div
        className="relative aspect-square bg-gray-100 rounded-t-lg overflow-hidden cursor-pointer"
        onClick={() => onSelect(suggestion.id)}
      >
        {imageThumbnail ? (
          <img
            src={imageThumbnail}
            alt={suggestion.original_filename}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Eye className="w-12 h-12 text-gray-300" />
          </div>
        )}

        {/* Selection Checkbox */}
        <div className="absolute top-2 left-2">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(suggestion.id)}
            className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        {/* Status Badge */}
        <div className="absolute top-2 right-2">
          <span
            className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor()}`}
          >
            {suggestion.status}
          </span>
        </div>

        {/* Confidence Score */}
        {suggestion.confidence_score !== null && (
          <div className="absolute bottom-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded flex items-center gap-1">
            <Sparkles className={`w-3 h-3 ${getConfidenceColor(suggestion.confidence_score)}`} />
            <span className={`text-xs font-medium ${getConfidenceColor(suggestion.confidence_score)}`}>
              {Math.round(suggestion.confidence_score * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Details */}
      <div className="p-4">
        {/* Original Filename */}
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Original</p>
          <p className="text-sm font-medium text-gray-700 truncate" title={suggestion.original_filename}>
            {suggestion.original_filename}
          </p>
        </div>

        {/* Suggested Filename - Editable */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-gray-500">Suggested</p>
            {!isEditing && suggestion.status === 'pending' && (
              <button
                onClick={() => setIsEditing(true)}
                className="text-blue-600 hover:text-blue-700 p-1"
                title="Edit suggestion"
              >
                <Edit2 className="w-3 h-3" />
              </button>
            )}
          </div>

          {isEditing ? (
            <div>
              <input
                type="text"
                value={editedFilename}
                onChange={(e) => setEditedFilename(e.target.value)}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveEdit()
                  if (e.key === 'Escape') handleCancelEdit()
                }}
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleSaveEdit}
                  className="flex-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="flex-1 px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm font-medium text-blue-600 truncate" title={suggestion.suggested_filename}>
              {suggestion.suggested_filename}
            </p>
          )}
        </div>

        {/* Description */}
        {suggestion.description && (
          <div className="mb-3">
            <p className="text-xs text-gray-600 line-clamp-2" title={suggestion.description}>
              {suggestion.description}
            </p>
          </div>
        )}

        {/* Folder */}
        <div className="mb-3">
          <p className="text-xs text-gray-400 truncate" title={suggestion.watched_folder_name}>
            📁 {suggestion.watched_folder_name}
          </p>
        </div>

        {/* Actions */}
        {suggestion.status === 'pending' && (
          <div className="flex gap-2">
            <button
              onClick={() => onApprove(suggestion.id)}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 transition-colors"
            >
              <Check className="w-4 h-4" />
              Approve
            </button>
            <button
              onClick={() => onReject(suggestion.id)}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 transition-colors"
            >
              <X className="w-4 h-4" />
              Reject
            </button>
          </div>
        )}

        {suggestion.status === 'approved' && (
          <div className="text-center py-2 text-sm text-green-600 font-medium">
            ✓ Approved - Ready for execution
          </div>
        )}

        {suggestion.status === 'rejected' && (
          <div className="text-center py-2 text-sm text-red-600 font-medium">
            ✗ Rejected
          </div>
        )}

        {suggestion.status === 'applied' && (
          <div className="text-center py-2 text-sm text-blue-600 font-medium">
            ✓ Successfully applied
          </div>
        )}

        {suggestion.status === 'failed' && (
          <div className="text-center py-2 text-sm text-red-600 font-medium">
            ✗ Failed to apply
          </div>
        )}
      </div>
    </div>
  )
}
