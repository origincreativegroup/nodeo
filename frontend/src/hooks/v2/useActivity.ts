/**
 * React Query hooks for activity log management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import * as api from '../../services/v2/api'

// Query keys
export const activityKeys = {
  all: ['activity'] as const,
  lists: () => [...activityKeys.all, 'list'] as const,
  list: (filters?: any) => [...activityKeys.lists(), filters] as const,
  stats: (days?: number) => [...activityKeys.all, 'stats', days] as const,
}

// List activity logs with filters
export function useActivityLog(params?: {
  folder_id?: string
  action_type?: string
  status?: string
  days?: number
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: activityKeys.list(params),
    queryFn: () => api.listActivityLog(params),
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

// Get activity statistics
export function useActivityStats(days: number = 7) {
  return useQuery({
    queryKey: activityKeys.stats(days),
    queryFn: () => api.getActivityStats(days),
    refetchInterval: 10000,
  })
}

// Rollback a rename operation
export function useRollbackRename() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (activityId: string) => api.rollbackRename(activityId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: activityKeys.lists() })
      queryClient.invalidateQueries({ queryKey: activityKeys.stats() })
      toast.success(
        `Rolled back: "${result.rolled_back_from}" → "${result.rolled_back_to}"`
      )
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to rollback rename')
    },
  })
}

// Export activity log
export function useExportActivityLog() {
  return useMutation({
    mutationFn: ({ format, days }: { format: 'csv' | 'json'; days?: number }) =>
      api.exportActivityLog(format, days),
    onSuccess: (blob, variables) => {
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `activity-log-${new Date().toISOString().split('T')[0]}.${variables.format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Activity log exported as ${variables.format.toUpperCase()}`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to export activity log')
    },
  })
}
