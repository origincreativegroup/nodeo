/**
 * Dialog for adding new watched folder
 */

import { useState } from 'react'
import { X, FolderOpen } from 'lucide-react'

interface AddFolderDialogProps {
  open: boolean
  onAdd: (path: string, name: string) => void
  onClose: () => void
  isLoading?: boolean
}

export default function AddFolderDialog({ open, onAdd, onClose, isLoading }: AddFolderDialogProps) {
  const [path, setPath] = useState('')
  const [name, setName] = useState('')

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (path.trim()) {
      onAdd(path.trim(), name.trim() || '')
      setPath('')
      setName('')
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      setPath('')
      setName('')
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <FolderOpen className="w-6 h-6 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">Add Watched Folder</h2>
            </div>
            <button
              onClick={handleClose}
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label htmlFor="folder-path" className="block text-sm font-medium text-gray-700 mb-2">
                Folder Path <span className="text-red-500">*</span>
              </label>
              <input
                id="folder-path"
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/path/to/folder"
                required
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter the absolute path to the folder you want to monitor
              </p>
            </div>

            <div>
              <label htmlFor="folder-name" className="block text-sm font-medium text-gray-700 mb-2">
                Display Name (Optional)
              </label>
              <input
                id="folder-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Photos"
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                If not provided, the folder name will be used
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">What happens next?</h4>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Folder will be monitored for new files</li>
                <li>• Existing files will be scanned automatically</li>
                <li>• AI analysis will run on each image</li>
                <li>• Rename suggestions will be generated</li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-4">
              <button
                type="submit"
                disabled={!path.trim() || isLoading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed font-medium"
              >
                {isLoading ? 'Adding...' : 'Add Folder'}
              </button>
              <button
                type="button"
                onClick={handleClose}
                disabled={isLoading}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
