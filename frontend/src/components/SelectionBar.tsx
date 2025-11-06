import { CheckSquare, Square, X } from 'lucide-react';

interface SelectionBarProps {
  selectedCount: number;
  totalCount: number;
  onSelectAll: () => void;
  onClearSelection: () => void;
  actions?: React.ReactNode;
  className?: string;
}

export default function SelectionBar({
  selectedCount,
  totalCount,
  onSelectAll,
  onClearSelection,
  actions,
  className = '',
}: SelectionBarProps) {
  const allSelected = selectedCount > 0 && selectedCount === totalCount;
  const someSelected = selectedCount > 0 && selectedCount < totalCount;

  return (
    <div className={`flex items-center justify-between bg-white p-4 rounded-lg shadow ${className}`}>
      <div className="flex items-center gap-4">
        {/* Select All / Deselect All Toggle */}
        <button
          onClick={allSelected ? onClearSelection : onSelectAll}
          className="flex items-center gap-2 text-gray-700 hover:text-gray-900 transition-colors"
          title={allSelected ? 'Deselect All' : 'Select All'}
        >
          {allSelected ? (
            <CheckSquare className="w-5 h-5 text-blue-600" />
          ) : someSelected ? (
            <CheckSquare className="w-5 h-5 text-blue-400" />
          ) : (
            <Square className="w-5 h-5" />
          )}
          <span className="text-sm font-medium">
            {allSelected ? 'Deselect All' : someSelected ? 'Select All' : 'Select All'}
          </span>
        </button>

        {/* Selection Count */}
        {selectedCount > 0 && (
          <>
            <div className="h-6 w-px bg-gray-300" />
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">
                <span className="font-semibold text-gray-900">{selectedCount}</span>
                {' '}of {totalCount} selected
              </span>
              <button
                onClick={onClearSelection}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="Clear selection"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
          </>
        )}
      </div>

      {/* Custom Actions */}
      {selectedCount > 0 && actions && (
        <div className="flex items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}
