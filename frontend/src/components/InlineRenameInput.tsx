import { useState, useEffect, useRef } from 'react';
import { Check, X, RotateCcw } from 'lucide-react';
import Button from './Button';

interface InlineRenameInputProps {
  currentName: string;
  suggestedName?: string;
  onAccept: (newName: string) => void;
  onRevert: () => void;
  onCancel?: () => void;
  isEditing?: boolean;
  className?: string;
}

export default function InlineRenameInput({
  currentName,
  suggestedName,
  onAccept,
  onRevert,
  onCancel,
  isEditing = false,
  className = '',
}: InlineRenameInputProps) {
  const [editMode, setEditMode] = useState(isEditing);
  const [editValue, setEditValue] = useState(suggestedName || currentName);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editMode && inputRef.current) {
      inputRef.current.focus();
      // Select filename without extension
      const lastDotIndex = editValue.lastIndexOf('.');
      if (lastDotIndex > 0) {
        inputRef.current.setSelectionRange(0, lastDotIndex);
      } else {
        inputRef.current.select();
      }
    }
  }, [editMode, editValue]);

  const handleAcceptSuggestion = () => {
    if (suggestedName) {
      onAccept(suggestedName);
    }
  };

  const handleEditClick = () => {
    setEditMode(true);
  };

  const handleSaveEdit = () => {
    if (editValue && editValue.trim() !== '') {
      onAccept(editValue);
      setEditMode(false);
    }
  };

  const handleCancelEdit = () => {
    setEditValue(suggestedName || currentName);
    setEditMode(false);
    onCancel?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  // Show current name with suggestion below (not in edit mode)
  if (!editMode && suggestedName && suggestedName !== currentName) {
    return (
      <div className={`space-y-2 ${className}`}>
        {/* Current filename */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 truncate">{currentName}</span>
        </div>

        {/* Suggested filename with actions */}
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-md px-2 py-1.5">
          <span className="text-sm font-medium text-green-700 flex-1 truncate" title={suggestedName}>
            {suggestedName}
          </span>

          {/* Action buttons */}
          <div className="flex items-center gap-1">
            <Button
              onClick={handleAcceptSuggestion}
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0 text-green-700 hover:bg-green-100"
              title="Accept suggested name"
            >
              <Check className="w-3.5 h-3.5" />
            </Button>

            <Button
              onClick={handleEditClick}
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0 text-blue-700 hover:bg-blue-100"
              title="Edit name"
            >
              <span className="text-xs font-bold">✎</span>
            </Button>

            <Button
              onClick={onRevert}
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0 text-gray-600 hover:bg-gray-100"
              title="Keep current name"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Edit mode
  if (editMode) {
    return (
      <div className={`space-y-2 ${className}`}>
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter filename"
          />

          <Button
            onClick={handleSaveEdit}
            size="sm"
            variant="primary"
            className="h-7 px-2"
            title="Save (Enter)"
          >
            <Check className="w-4 h-4" />
          </Button>

          <Button
            onClick={handleCancelEdit}
            size="sm"
            variant="ghost"
            className="h-7 px-2"
            title="Cancel (Esc)"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-gray-500">
          Press Enter to save, Esc to cancel
        </p>
      </div>
    );
  }

  // Default: just show current name
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-sm text-gray-900 truncate">{currentName}</span>
    </div>
  );
}
