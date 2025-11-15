/**
 * Folder Monitoring Dashboard - Main page for v2 automated folder watching
 */

import { useState, useEffect } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import { useFolders, useFolderStats, useAddFolder, useUpdateFolder, useDeleteFolder, useRescanFolder, useUpdateFolderFromWebSocket } from '../../hooks/v2/useFolders'
import { useWebSocket } from '../../hooks/v2/useWebSocket'
import FolderCard from '../../components/v2/folders/FolderCard'
import FolderStats from '../../components/v2/folders/FolderStats'
import AddFolderDialog from '../../components/v2/folders/AddFolderDialog'
import type { WatchedFolder } from '../../types/v2'

export default function FolderMonitoring() {
  const [showAddDialog, setShowAddDialog] = useState(false)

  // Data fetching
  const { data: folders, isLoading: foldersLoading, refetch } = useFolders()
  const { data: stats, isLoading: statsLoading } = useFolderStats()

  // Mutations
  const addFolderMutation = useAddFolder()
  const updateFolderMutation = useUpdateFolder()
  const deleteFolderMutation = useDeleteFolder()
  const rescanFolderMutation = useRescanFolder()

  // WebSocket for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws/progress', true)
  const updateFolderFromWebSocket = useUpdateFolderFromWebSocket()

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage?.type === 'progress_update' && lastMessage.folders) {
      updateFolderFromWebSocket(lastMessage.folders)
    }
  }, [lastMessage, updateFolderFromWebSocket])

  // Handlers
  const handleAddFolder = async (path: string, name?: string) => {
    await addFolderMutation.mutateAsync({ path, name })
    setShowAddDialog(false)
  }

  const handlePauseFolder = (folderId: string) => {
    updateFolderMutation.mutate({ folderId, data: { status: 'paused' } })
  }

  const handleResumeFolder = (folderId: string) => {
    updateFolderMutation.mutate({ folderId, data: { status: 'active' } })
  }

  const handleRescanFolder = (folderId: string) => {
    rescanFolderMutation.mutate(folderId)
  }

  const handleDeleteFolder = (folderId: string) => {
    deleteFolderMutation.mutate(folderId)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Folder Monitoring</h1>
            <p className="mt-2 text-gray-600">
              Automated file detection and AI-powered rename suggestions
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* WebSocket Status */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              isConnected ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              }`} />
              <span className="text-sm font-medium">
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            {/* Add Folder Button */}
            <button
              onClick={() => setShowAddDialog(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Add Folder</span>
            </button>
          </div>
        </div>

        {/* Statistics */}
        <FolderStats stats={stats} isLoading={statsLoading} />

        {/* Folder List */}
        {foldersLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : folders && folders.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {folders.map((folder: WatchedFolder) => (
              <FolderCard
                key={folder.id}
                folder={folder}
                onPause={handlePauseFolder}
                onResume={handleResumeFolder}
                onRescan={handleRescanFolder}
                onDelete={handleDeleteFolder}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <Plus className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No Folders Being Monitored
              </h3>
              <p className="text-gray-600 mb-6">
                Add a folder to start automatic file detection and AI-powered rename suggestions
              </p>
              <button
                onClick={() => setShowAddDialog(true)}
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-5 h-5" />
                Add Your First Folder
              </button>
            </div>
          </div>
        )}

        {/* Help Text */}
        {folders && folders.length > 0 && (
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">💡 How it works</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• <strong>Real-time Detection:</strong> New files are automatically detected when added to watched folders</li>
              <li>• <strong>AI Analysis:</strong> Each image is analyzed to extract description, tags, and scene information</li>
              <li>• <strong>Smart Suggestions:</strong> Rename suggestions are generated with confidence scores (minimum {(stats?.total_files || 0) > 0 ? '50%' : '50%'})</li>
              <li>• <strong>Live Updates:</strong> Progress is shown in real-time via WebSocket connection</li>
            </ul>
          </div>
        )}
      </div>

      {/* Add Folder Dialog */}
      <AddFolderDialog
        open={showAddDialog}
        onAdd={handleAddFolder}
        onClose={() => setShowAddDialog(false)}
        isLoading={addFolderMutation.isPending}
      />
    </div>
  )
}
