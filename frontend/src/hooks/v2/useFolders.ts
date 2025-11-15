/**
 * React Query hooks for folder management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import * as api from '../../services/v2/api'
import type { WatchedFolder } from '../../types/v2'

// Query keys
export const folderKeys = {
  all: ['folders'] as const,
  lists: () => [...folderKeys.all, 'list'] as const,
  list: () => [...folderKeys.lists()] as const,
  details: () => [...folderKeys.all, 'detail'] as const,
  detail: (id: string) => [...folderKeys.details(), id] as const,
  stats: () => [...folderKeys.all, 'stats'] as const,
}

// List all watched folders
export function useFolders() {
  return useQuery({
    queryKey: folderKeys.list(),
    queryFn: api.listWatchedFolders,
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

// Get folder statistics
export function useFolderStats() {
  return useQuery({
    queryKey: folderKeys.stats(),
    queryFn: api.getFolderStats,
    refetchInterval: 10000,
  })
}

// Get single folder details
export function useFolder(folderId: string | null) {
  return useQuery({
    queryKey: folderKeys.detail(folderId || ''),
    queryFn: () => api.getFolder(folderId!),
    enabled: !!folderId,
  })
}

// Add new watched folder
export function useAddFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ path, name }: { path: string; name?: string }) =>
      api.addWatchedFolder(path, name),
    onSuccess: (newFolder: WatchedFolder) => {
      queryClient.invalidateQueries({ queryKey: folderKeys.lists() })
      queryClient.invalidateQueries({ queryKey: folderKeys.stats() })
      toast.success(`Folder "${newFolder.name}" added successfully!`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add folder')
    },
  })
}

// Update folder (pause/resume/rename)
export function useUpdateFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ folderId, data }: { folderId: string; data: { name?: string; status?: string } }) =>
      api.updateFolder(folderId, data),
    onSuccess: (updatedFolder: WatchedFolder) => {
      queryClient.invalidateQueries({ queryKey: folderKeys.lists() })
      queryClient.invalidateQueries({ queryKey: folderKeys.detail(updatedFolder.id) })
      queryClient.invalidateQueries({ queryKey: folderKeys.stats() })
      toast.success('Folder updated successfully!')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update folder')
    },
  })
}

// Delete watched folder
export function useDeleteFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (folderId: string) => api.deleteFolder(folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.lists() })
      queryClient.invalidateQueries({ queryKey: folderKeys.stats() })
      toast.success('Folder removed successfully!')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove folder')
    },
  })
}

// Trigger folder rescan
export function useRescanFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (folderId: string) => api.rescanFolder(folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderKeys.lists() })
      toast.success('Rescan initiated!')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to trigger rescan')
    },
  })
}

// Update folder data from WebSocket
export function useUpdateFolderFromWebSocket() {
  const queryClient = useQueryClient()

  return (folderUpdates: Array<{
    folder_id: string
    status: string
    progress: number
    file_count: number
    analyzed_count: number
    pending_count: number
  }>) => {
    const currentFolders = queryClient.getQueryData<WatchedFolder[]>(folderKeys.list())

    if (!currentFolders) return

    const updatedFolders = currentFolders.map((folder) => {
      const update = folderUpdates.find((u) => u.folder_id === folder.id)
      if (!update) return folder

      return {
        ...folder,
        status: update.status as any,
        file_count: update.file_count,
        analyzed_count: update.analyzed_count,
        pending_count: update.pending_count,
      }
    })

    queryClient.setQueryData(folderKeys.list(), updatedFolders)
  }
}
