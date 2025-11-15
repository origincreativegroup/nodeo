/**
 * Type definitions for JSPOW v2 - Automated Folder Monitoring
 */

export type WatchedFolderStatus = 'active' | 'paused' | 'error' | 'scanning'

export type SuggestionStatus = 'pending' | 'approved' | 'rejected' | 'applied' | 'failed'

export type ActivityActionType =
  | 'rename'
  | 'approve'
  | 'reject'
  | 'scan'
  | 'error'
  | 'folder_added'
  | 'folder_removed'

export interface WatchedFolder {
  id: string
  path: string
  name: string
  status: WatchedFolderStatus
  file_count: number
  analyzed_count: number
  pending_count: number
  last_scan_at: string | null
  error_message: string | null
  created_at: string
  updated_at: string | null
}

export interface FolderStats {
  total_folders: number
  active_folders: number
  paused_folders: number
  error_folders: number
  scanning_folders: number
  total_files: number
  total_analyzed: number
  total_pending: number
}

export interface RenameSuggestion {
  id: string
  watched_folder_id: string
  watched_folder_name: string
  asset_id: number | null
  original_path: string
  original_filename: string
  suggested_filename: string
  description: string | null
  confidence_score: number | null
  status: SuggestionStatus
  created_at: string
  updated_at: string | null
}

export interface ActivityLog {
  id: string
  watched_folder_id: string | null
  watched_folder_name: string | null
  asset_id: number | null
  action_type: ActivityActionType
  original_filename: string | null
  new_filename: string | null
  folder_path: string | null
  status: string
  error_message: string | null
  metadata: Record<string, any> | null
  created_at: string
}

export interface SuggestionsStats {
  total: number
  pending: number
  approved: number
  rejected: number
  applied: number
  failed: number
  average_confidence: number
}

export interface ActivityStats {
  period_days: number
  total_activities: number
  by_action: Record<string, number>
  by_status: Record<string, number>
  success_rate: number
}

export interface WebSocketProgress {
  type: 'progress_update' | 'connected' | 'ping' | 'pong'
  timestamp?: number
  watcher_status?: {
    running: boolean
    active_watchers: number
    queue_size: number
  }
  folders?: Array<{
    folder_id: string
    status: WatchedFolderStatus
    progress: number
    file_count: number
    analyzed_count: number
    pending_count: number
  }>
}
