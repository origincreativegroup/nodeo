/**
 * React Query hooks for rename suggestions management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import * as api from '../../services/v2/api'
import type { RenameSuggestion } from '../../types/v2'

// Query keys
export const suggestionKeys = {
  all: ['suggestions'] as const,
  lists: () => [...suggestionKeys.all, 'list'] as const,
  list: (filters?: any) => [...suggestionKeys.lists(), filters] as const,
  details: () => [...suggestionKeys.all, 'detail'] as const,
  detail: (id: string) => [...suggestionKeys.details(), id] as const,
  stats: () => [...suggestionKeys.all, 'stats'] as const,
}

// List suggestions with filters
export function useSuggestions(params?: {
  folder_id?: string
  status?: string
  min_confidence?: number
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: suggestionKeys.list(params),
    queryFn: () => api.listSuggestions(params),
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  })
}

// Get suggestions statistics
export function useSuggestionsStats() {
  return useQuery({
    queryKey: suggestionKeys.stats(),
    queryFn: api.getSuggestionsStats,
    refetchInterval: 10000,
  })
}

// Get single suggestion
export function useSuggestion(suggestionId: string | null) {
  return useQuery({
    queryKey: suggestionKeys.detail(suggestionId || ''),
    queryFn: () => api.getSuggestion(suggestionId!),
    enabled: !!suggestionId,
  })
}

// Update suggestion filename
export function useUpdateSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ suggestionId, filename }: { suggestionId: string; filename: string }) =>
      api.updateSuggestion(suggestionId, filename),
    onSuccess: (updatedSuggestion: RenameSuggestion) => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.detail(updatedSuggestion.id) })
      toast.success('Suggestion updated successfully!')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update suggestion')
    },
  })
}

// Approve single suggestion
export function useApproveSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (suggestionId: string) => api.approveSuggestion(suggestionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      toast.success('Suggestion approved!')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to approve suggestion')
    },
  })
}

// Reject single suggestion
export function useRejectSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (suggestionId: string) => api.rejectSuggestion(suggestionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      toast.success('Suggestion rejected')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reject suggestion')
    },
  })
}

// Batch approve suggestions
export function useBatchApproveSuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (suggestionIds: string[]) => api.batchApproveSuggestions(suggestionIds),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      toast.success(
        `Approved ${result.approved_count} of ${result.total_requested} suggestions`
      )
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to batch approve')
    },
  })
}

// Batch reject suggestions
export function useBatchRejectSuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (suggestionIds: string[]) => api.batchRejectSuggestions(suggestionIds),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      toast.success(`Rejected ${result.rejected_count} of ${result.total_requested} suggestions`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to batch reject')
    },
  })
}

// Execute single rename
export function useExecuteSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ suggestionId, createBackup = true }: { suggestionId: string; createBackup?: boolean }) =>
      api.executeSuggestion(suggestionId, createBackup),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      toast.success(`Renamed "${result.old_filename}" to "${result.new_filename}"`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to execute rename')
    },
  })
}

// Batch execute renames
export function useBatchExecuteSuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ suggestionIds, createBackups = true }: { suggestionIds: string[]; createBackups?: boolean }) =>
      api.batchExecuteSuggestions(suggestionIds, createBackups),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: suggestionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: suggestionKeys.stats() })
      if (result.failed > 0) {
        toast.error(`Renamed ${result.succeeded} files, ${result.failed} failed`)
      } else {
        toast.success(`Successfully renamed ${result.succeeded} files`)
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to batch execute')
    },
  })
}
