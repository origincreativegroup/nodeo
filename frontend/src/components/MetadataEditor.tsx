import { useState, useEffect } from 'react';
import { Tag, X, Save, Edit2 } from 'lucide-react';
import Button from './Button';

interface ImageMetadata {
  id: number;
  ai_description?: string;
  ai_scene?: string;
  ai_tags?: string[];
  ai_objects?: string[];
  title?: string;
  description?: string;
  alt_text?: string;
  custom_tags?: string[];
}

interface MetadataEditorProps {
  metadata: ImageMetadata;
  mode?: 'view' | 'edit';
  onSave?: (metadata: Partial<ImageMetadata>) => void;
  onCancel?: () => void;
  className?: string;
  compact?: boolean;
}

export default function MetadataEditor({
  metadata,
  mode: initialMode = 'view',
  onSave,
  onCancel,
  className = '',
  compact = false,
}: MetadataEditorProps) {
  const [mode, setMode] = useState<'view' | 'edit'>(initialMode);
  const [editedData, setEditedData] = useState<Partial<ImageMetadata>>({});
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  const handleEdit = () => {
    setEditedData({
      title: metadata.title || '',
      description: metadata.description || '',
      alt_text: metadata.alt_text || '',
      custom_tags: metadata.custom_tags || [],
    });
    setMode('edit');
  };

  const handleSave = () => {
    if (onSave) {
      onSave(editedData);
    }
    setMode('view');
  };

  const handleCancel = () => {
    setEditedData({});
    setMode('view');
    if (onCancel) {
      onCancel();
    }
  };

  const handleAddTag = () => {
    if (newTag.trim() && editedData.custom_tags) {
      setEditedData({
        ...editedData,
        custom_tags: [...editedData.custom_tags, newTag.trim()],
      });
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedData({
      ...editedData,
      custom_tags: editedData.custom_tags?.filter(tag => tag !== tagToRemove) || [],
    });
  };

  const displayValue = (key: keyof ImageMetadata) => {
    return mode === 'edit' && editedData[key] !== undefined
      ? editedData[key]
      : metadata[key];
  };

  if (compact) {
    return (
      <div className={`space-y-2 ${className}`}>
        {/* AI Description */}
        {metadata.ai_description && (
          <div className="text-sm text-gray-600">
            <p className="line-clamp-2">{metadata.ai_description}</p>
          </div>
        )}

        {/* Tags */}
        {(metadata.ai_tags || metadata.custom_tags) && (
          <div className="flex flex-wrap gap-1">
            {metadata.ai_tags?.slice(0, 3).map((tag, idx) => (
              <span
                key={`ai-${idx}`}
                className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs"
              >
                {tag}
              </span>
            ))}
            {metadata.custom_tags?.slice(0, 2).map((tag, idx) => (
              <span
                key={`custom-${idx}`}
                className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Mode Toggle */}
      {mode === 'view' && onSave && (
        <div className="flex justify-end">
          <Button
            onClick={handleEdit}
            variant="ghost"
            size="sm"
          >
            <Edit2 className="w-4 h-4 mr-2" />
            Edit Metadata
          </Button>
        </div>
      )}

      {/* AI-Generated Metadata (Read-Only) */}
      {metadata.ai_description && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AI Description
            <span className="ml-2 text-xs text-blue-600 font-normal">(AI Generated)</span>
          </label>
          <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded-lg">
            {metadata.ai_description}
          </p>
        </div>
      )}

      {/* AI Scene */}
      {metadata.ai_scene && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Scene Type
            <span className="ml-2 text-xs text-blue-600 font-normal">(AI Generated)</span>
          </label>
          <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
            {metadata.ai_scene}
          </span>
        </div>
      )}

      {/* AI Tags (Read-Only) */}
      {metadata.ai_tags && metadata.ai_tags.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            AI Tags
          </label>
          <div className="flex flex-wrap gap-2">
            {metadata.ai_tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm flex items-center gap-1"
              >
                <Tag className="w-3 h-3" />
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Editable Title */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Title
        </label>
        {mode === 'edit' ? (
          <input
            type="text"
            value={(displayValue('title') as string) || ''}
            onChange={(e) => setEditedData({ ...editedData, title: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter a title..."
          />
        ) : (
          <p className="text-sm text-gray-600">{displayValue('title') || 'No title set'}</p>
        )}
      </div>

      {/* Editable Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        {mode === 'edit' ? (
          <textarea
            value={(displayValue('description') as string) || ''}
            onChange={(e) => setEditedData({ ...editedData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter a description..."
          />
        ) : (
          <p className="text-sm text-gray-600 whitespace-pre-wrap">
            {displayValue('description') || 'No description set'}
          </p>
        )}
      </div>

      {/* Editable Alt Text */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Alt Text (for accessibility)
        </label>
        {mode === 'edit' ? (
          <input
            type="text"
            value={(displayValue('alt_text') as string) || ''}
            onChange={(e) => setEditedData({ ...editedData, alt_text: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Describe the image for screen readers..."
          />
        ) : (
          <p className="text-sm text-gray-600">{displayValue('alt_text') || 'No alt text set'}</p>
        )}
      </div>

      {/* Custom Tags (Editable) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Custom Tags
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {(displayValue('custom_tags') as string[] || []).map((tag, idx) => (
            <span
              key={idx}
              className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm flex items-center gap-1"
            >
              {tag}
              {mode === 'edit' && (
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:bg-green-200 rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </span>
          ))}
        </div>
        {mode === 'edit' && (
          <div className="flex gap-2">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="Add a tag..."
            />
            <Button onClick={handleAddTag} variant="secondary" size="sm">
              Add
            </Button>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {mode === 'edit' && (
        <div className="flex gap-2 pt-4 border-t">
          <Button onClick={handleSave} className="flex-1">
            <Save className="w-4 h-4 mr-2" />
            Save Changes
          </Button>
          <Button onClick={handleCancel} variant="ghost">
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}
