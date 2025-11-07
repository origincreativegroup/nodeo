import { useState, useEffect } from 'react'
import { Save, AlertCircle, FileText } from 'lucide-react'
import Modal from './Modal'
import Button from './Button'
import { ImageData } from '../context/AppContext'

export interface BulkRenamePattern {
  find: string
  replace: string
  useRegex: boolean
  caseSensitive: boolean
}

interface BulkRenameModalProps {
  isOpen: boolean
  onClose: () => void
  images: ImageData[]
  onApply: (pattern: BulkRenamePattern) => Promise<void>
}

export default function BulkRenameModal({
  isOpen,
  onClose,
  images,
  onApply,
}: BulkRenameModalProps) {
  const [pattern, setPattern] = useState<BulkRenamePattern>({
    find: '',
    replace: '',
    useRegex: false,
    caseSensitive: false,
  })
  const [previews, setPreviews] = useState<Array<{ original: string; new: string }>>([])
  const [applying, setApplying] = useState(false)

  // Generate preview when pattern changes
  useEffect(() => {
    if (!pattern.find) {
      setPreviews([])
      return
    }

    const newPreviews = images.map((img) => {
      const original = img.current_filename || img.filename
      let newName = original

      try {
        if (pattern.useRegex) {
          const flags = pattern.caseSensitive ? 'g' : 'gi'
          const regex = new RegExp(pattern.find, flags)
          newName = original.replace(regex, pattern.replace)
        } else {
          if (pattern.caseSensitive) {
            newName = original.split(pattern.find).join(pattern.replace)
          } else {
            const regex = new RegExp(
              pattern.find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
              'gi'
            )
            newName = original.replace(regex, pattern.replace)
          }
        }
      } catch (error) {
        // Invalid regex
        newName = original
      }

      return { original, new: newName }
    })

    setPreviews(newPreviews)
  }, [pattern, images])

  const handleApply = async () => {
    if (!pattern.find) {
      return
    }

    setApplying(true)
    try {
      await onApply(pattern)
      onClose()
      setPattern({ find: '', replace: '', useRegex: false, caseSensitive: false })
    } catch (error) {
      console.error('Bulk rename error:', error)
    } finally {
      setApplying(false)
    }
  }

  const changedCount = previews.filter((p) => p.original !== p.new).length

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Bulk Rename Files"
      size="lg"
      footer={
        <div className="flex justify-between items-center w-full">
          <div className="text-sm text-gray-600">
            {changedCount} of {images.length} files will be renamed
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose} disabled={applying}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleApply}
              icon={<Save className="w-5 h-5" />}
              loading={applying}
              disabled={!pattern.find || changedCount === 0}
            >
              Apply Rename
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Bulk Rename Selected Files</p>
              <p>
                Find and replace text in {images.length} selected{' '}
                {images.length === 1 ? 'filename' : 'filenames'}. You can use plain text or
                regular expressions.
              </p>
            </div>
          </div>
        </div>

        {/* Pattern Input */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Find text
            </label>
            <input
              type="text"
              value={pattern.find}
              onChange={(e) => setPattern((prev) => ({ ...prev, find: e.target.value }))}
              placeholder="Text to find..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Replace with
            </label>
            <input
              type="text"
              value={pattern.replace}
              onChange={(e) => setPattern((prev) => ({ ...prev, replace: e.target.value }))}
              placeholder="Replacement text..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Options */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={pattern.useRegex}
                onChange={(e) =>
                  setPattern((prev) => ({ ...prev, useRegex: e.target.checked }))
                }
                className="rounded"
              />
              Use regular expressions
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={pattern.caseSensitive}
                onChange={(e) =>
                  setPattern((prev) => ({ ...prev, caseSensitive: e.target.checked }))
                }
                className="rounded"
              />
              Case sensitive
            </label>
          </div>
        </div>

        {/* Preview */}
        {previews.length > 0 && (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Preview ({changedCount} changed)
              </h4>
            </div>
            <div className="max-h-96 overflow-y-auto divide-y divide-gray-200">
              {previews
                .filter((p) => p.original !== p.new)
                .slice(0, 50)
                .map((preview, idx) => (
                  <div key={idx} className="px-4 py-3">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-gray-500">From:</span>
                      <span className="font-mono text-gray-700">{preview.original}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm mt-1">
                      <span className="text-gray-500">To:</span>
                      <span className="font-mono text-green-700 font-medium">
                        {preview.new}
                      </span>
                    </div>
                  </div>
                ))}
              {changedCount > 50 && (
                <div className="px-4 py-3 text-sm text-gray-500 text-center">
                  ... and {changedCount - 50} more files
                </div>
              )}
            </div>
          </div>
        )}

        {pattern.find && changedCount === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p>No files will be changed with this pattern</p>
          </div>
        )}
      </div>
    </Modal>
  )
}
