/**
 * API client for JSPOW v2 endpoints
 */

import type {
  WatchedFolder,
  FolderStats,
  RenameSuggestion,
  ActivityLog,
  SuggestionsStats,
  ActivityStats,
} from '../../types/v2'

const API_BASE = '/api/v2'

// ============================================================================
// Folder Management
// ============================================================================

export async function addWatchedFolder(path: string, name?: string): Promise<WatchedFolder> {
  const response = await fetch(`${API_BASE}/folders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, name }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to add folder')
  }

  return response.json()
}

export async function listWatchedFolders(): Promise<WatchedFolder[]> {
  const response = await fetch(`${API_BASE}/folders`)

  if (!response.ok) {
    throw new Error('Failed to fetch folders')
  }

  return response.json()
}

export async function getFolderStats(): Promise<FolderStats> {
  const response = await fetch(`${API_BASE}/folders/stats`)

  if (!response.ok) {
    throw new Error('Failed to fetch folder stats')
  }

  return response.json()
}

export async function getFolder(folderId: string): Promise<WatchedFolder> {
  const response = await fetch(`${API_BASE}/folders/${folderId}`)

  if (!response.ok) {
    throw new Error('Failed to fetch folder')
  }

  return response.json()
}

export async function updateFolder(
  folderId: string,
  data: { name?: string; status?: string }
): Promise<WatchedFolder> {
  const response = await fetch(`${API_BASE}/folders/${folderId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update folder')
  }

  return response.json()
}

export async function deleteFolder(folderId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/folders/${folderId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete folder')
  }
}

export async function rescanFolder(folderId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/folders/${folderId}/rescan`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('Failed to trigger rescan')
  }

  return response.json()
}

// ============================================================================
// Rename Suggestions
// ============================================================================

export async function listSuggestions(params?: {
  folder_id?: string
  status?: string
  min_confidence?: number
  limit?: number
  offset?: number
}): Promise<RenameSuggestion[]> {
  const queryParams = new URLSearchParams()
  if (params?.folder_id) queryParams.set('folder_id', params.folder_id)
  if (params?.status) queryParams.set('status_filter', params.status)
  if (params?.min_confidence !== undefined)
    queryParams.set('min_confidence', params.min_confidence.toString())
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())

  const url = `${API_BASE}/suggestions${queryParams.toString() ? '?' + queryParams : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error('Failed to fetch suggestions')
  }

  return response.json()
}

export async function getSuggestion(suggestionId: string): Promise<RenameSuggestion> {
  const response = await fetch(`${API_BASE}/suggestions/${suggestionId}`)

  if (!response.ok) {
    throw new Error('Failed to fetch suggestion')
  }

  return response.json()
}

export async function updateSuggestion(
  suggestionId: string,
  suggestedFilename: string
): Promise<RenameSuggestion> {
  const response = await fetch(`${API_BASE}/suggestions/${suggestionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggested_filename: suggestedFilename }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update suggestion')
  }

  return response.json()
}

export async function approveSuggestion(suggestionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/suggestions/${suggestionId}/approve`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('Failed to approve suggestion')
  }

  return response.json()
}

export async function rejectSuggestion(suggestionId: string): Promise<{ message: string }> {
  const response = await fetch(`${API_BASE}/suggestions/${suggestionId}/reject`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('Failed to reject suggestion')
  }

  return response.json()
}

export async function batchApproveSuggestions(suggestionIds: string[]): Promise<{
  message: string
  approved_count: number
  total_requested: number
}> {
  const response = await fetch(`${API_BASE}/suggestions/batch-approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestion_ids: suggestionIds }),
  })

  if (!response.ok) {
    throw new Error('Failed to batch approve')
  }

  return response.json()
}

export async function batchRejectSuggestions(suggestionIds: string[]): Promise<{
  message: string
  rejected_count: number
  total_requested: number
}> {
  const response = await fetch(`${API_BASE}/suggestions/batch-reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ suggestion_ids: suggestionIds }),
  })

  if (!response.ok) {
    throw new Error('Failed to batch reject')
  }

  return response.json()
}

export async function executeSuggestion(
  suggestionId: string,
  createBackup: boolean = true
): Promise<{
  success: boolean
  old_filename: string
  new_filename: string
  asset_id: number
}> {
  const response = await fetch(
    `${API_BASE}/suggestions/${suggestionId}/execute?create_backup=${createBackup}`,
    {
      method: 'POST',
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to execute rename')
  }

  return response.json()
}

export async function batchExecuteSuggestions(
  suggestionIds: string[],
  createBackups: boolean = true
): Promise<{
  total: number
  succeeded: number
  failed: number
  results: Array<any>
}> {
  const response = await fetch(
    `${API_BASE}/suggestions/batch-execute?create_backups=${createBackups}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suggestion_ids: suggestionIds }),
    }
  )

  if (!response.ok) {
    throw new Error('Failed to batch execute')
  }

  return response.json()
}

export async function getSuggestionsStats(): Promise<SuggestionsStats> {
  const response = await fetch(`${API_BASE}/suggestions/stats/summary`)

  if (!response.ok) {
    throw new Error('Failed to fetch suggestions stats')
  }

  return response.json()
}

// ============================================================================
// Activity Log
// ============================================================================

export async function listActivityLog(params?: {
  folder_id?: string
  action_type?: string
  status?: string
  days?: number
  limit?: number
  offset?: number
}): Promise<ActivityLog[]> {
  const queryParams = new URLSearchParams()
  if (params?.folder_id) queryParams.set('folder_id', params.folder_id)
  if (params?.action_type) queryParams.set('action_type', params.action_type)
  if (params?.status) queryParams.set('status_filter', params.status)
  if (params?.days) queryParams.set('days', params.days.toString())
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())

  const url = `${API_BASE}/activity${queryParams.toString() ? '?' + queryParams : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error('Failed to fetch activity log')
  }

  return response.json()
}

export async function getActivityStats(days: number = 7): Promise<ActivityStats> {
  const response = await fetch(`${API_BASE}/activity/stats?days=${days}`)

  if (!response.ok) {
    throw new Error('Failed to fetch activity stats')
  }

  return response.json()
}

export async function exportActivityLog(
  format: 'csv' | 'json' = 'csv',
  days: number = 30
): Promise<Blob> {
  const response = await fetch(`${API_BASE}/activity/export?format=${format}&days=${days}`)

  if (!response.ok) {
    throw new Error('Failed to export activity log')
  }

  return response.blob()
}

export async function rollbackRename(activityId: string): Promise<{
  success: boolean
  rolled_back_from: string
  rolled_back_to: string
  asset_id: number
}> {
  const response = await fetch(`${API_BASE}/activity/${activityId}/rollback`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to rollback rename')
  }

  return response.json()
}
