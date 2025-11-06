import { useState } from 'react';
import { Check, Trash2, Eye, Edit, MoreVertical } from 'lucide-react';
import Button from './Button';
import { ImageData } from '../context/AppContext';

type ImageCardVariant = 'grid' | 'list' | 'compact';

interface ImageCardProps {
  image: ImageData;
  variant?: ImageCardVariant;
  selected?: boolean;
  onSelect?: (id: number) => void;
  onDelete?: (id: number) => void;
  onView?: (image: ImageData) => void;
  onEdit?: (image: ImageData) => void;
  showActions?: boolean;
  className?: string;
}

export default function ImageCard({
  image,
  variant = 'grid',
  selected = false,
  onSelect,
  onDelete,
  onView,
  onEdit,
  showActions = true,
  className = '',
}: ImageCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  const thumbnailUrl = `/api/images/${image.id}/thumbnail`;
  const sizeInMB = (image.file_size / (1024 * 1024)).toFixed(2);
  const dimensions = image.width && image.height ? `${image.width}×${image.height}` : 'Unknown';
  const displayName = image.current_filename || image.filename;

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSelect) {
      onSelect(image.id);
    }
  };

  // Grid variant - thumbnail with overlay
  if (variant === 'grid') {
    return (
      <div
        className={`group relative bg-white rounded-lg shadow hover:shadow-lg transition-shadow ${
          selected ? 'ring-2 ring-blue-500' : ''
        } ${className}`}
        onClick={() => onView?.(image)}
      >
        <div className="relative aspect-square overflow-hidden rounded-t-lg bg-gray-100">
          <img
            src={thumbnailUrl}
            alt={displayName}
            className="w-full h-full object-cover"
            loading="lazy"
          />

          {onSelect && (
            <div className="absolute top-2 left-2 z-10" onClick={handleCheckboxClick}>
              <div
                className={`w-6 h-6 rounded border-2 flex items-center justify-center cursor-pointer transition-colors ${
                  selected
                    ? 'bg-blue-500 border-blue-500'
                    : 'bg-white border-gray-300 hover:border-blue-500'
                }`}
              >
                {selected && <Check className="w-4 h-4 text-white" />}
              </div>
            </div>
          )}

          {image.analyzed_at && (
            <div className="absolute top-2 right-2">
              <span className="px-2 py-1 bg-blue-500 text-white text-xs rounded-full">
                AI
              </span>
            </div>
          )}

          {showActions && (
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              {onView && (
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onView(image);
                  }}
                  size="sm"
                  variant="secondary"
                >
                  <Eye className="w-4 h-4" />
                </Button>
              )}
              {onDelete && (
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(image.id);
                  }}
                  size="sm"
                  variant="danger"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          )}
        </div>

        <div className="p-3">
          <p className="text-sm font-medium text-gray-900 truncate" title={displayName}>
            {displayName}
          </p>
          <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
            <span>{dimensions}</span>
            <span>{sizeInMB} MB</span>
          </div>

          {image.ai_tags && image.ai_tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {image.ai_tags.slice(0, 2).map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs"
                >
                  {tag}
                </span>
              ))}
              {image.ai_tags.length > 2 && (
                <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                  +{image.ai_tags.length - 2}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // List variant
  if (variant === 'list') {
    return (
      <div
        className={`group flex items-center gap-4 bg-white rounded-lg p-4 shadow hover:shadow-md transition-shadow ${
          selected ? 'ring-2 ring-blue-500' : ''
        } ${className}`}
      >
        {onSelect && (
          <div onClick={handleCheckboxClick}>
            <div
              className={`w-6 h-6 rounded border-2 flex items-center justify-center cursor-pointer transition-colors ${
                selected
                  ? 'bg-blue-500 border-blue-500'
                  : 'bg-white border-gray-300 hover:border-blue-500'
              }`}
            >
              {selected && <Check className="w-4 h-4 text-white" />}
            </div>
          </div>
        )}

        <div className="relative w-20 h-20 flex-shrink-0">
          <img
            src={thumbnailUrl}
            alt={displayName}
            className="w-full h-full object-cover rounded-lg"
            loading="lazy"
          />
          {image.analyzed_at && (
            <div className="absolute -top-1 -right-1">
              <div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-white" />
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate">
            {image.current_filename || displayName}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {dimensions} • {sizeInMB} MB
          </p>

          {image.ai_description && (
            <p className="text-xs text-gray-600 mt-2 line-clamp-2">
              {image.ai_description}
            </p>
          )}

          {image.ai_tags && image.ai_tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {image.ai_tags.slice(0, 3).map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {showActions && (
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {onEdit && (
              <Button onClick={() => onEdit(image)} size="sm" variant="ghost" title="Edit">
                <Edit className="w-4 h-4" />
              </Button>
            )}
            {onView && (
              <Button onClick={() => onView(image)} size="sm" variant="ghost" title="View">
                <Eye className="w-4 h-4" />
              </Button>
            )}
            {onDelete && (
              <Button onClick={() => onDelete(image.id)} size="sm" variant="ghost" title="Delete">
                <Trash2 className="w-4 h-4 text-red-600" />
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }

  // Compact variant
  if (variant === 'compact') {
    return (
      <div
        className={`group flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors ${
          selected ? 'bg-blue-50' : ''
        } ${className}`}
      >
        {onSelect && (
          <div onClick={handleCheckboxClick}>
            <div
              className={`w-5 h-5 rounded border-2 flex items-center justify-center cursor-pointer transition-colors ${
                selected
                  ? 'bg-blue-500 border-blue-500'
                  : 'bg-white border-gray-300 hover:border-blue-500'
              }`}
            >
              {selected && <Check className="w-3 h-3 text-white" />}
            </div>
          </div>
        )}

        <div className="w-12 h-12 flex-shrink-0">
          <img
            src={thumbnailUrl}
            alt={displayName}
            className="w-full h-full object-cover rounded"
            loading="lazy"
          />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {displayName}
          </p>
          <p className="text-xs text-gray-500">
            {dimensions}
          </p>
        </div>

        {showActions && (
          <div className="relative">
            <Button onClick={() => setShowMenu(!showMenu)} size="sm" variant="ghost">
              <MoreVertical className="w-4 h-4" />
            </Button>

            {showMenu && (
              <div className="absolute right-0 mt-1 w-32 bg-white rounded-lg shadow-lg border z-10">
                {onView && (
                  <button
                    onClick={() => {
                      onView(image);
                      setShowMenu(false);
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                )}
                {onEdit && (
                  <button
                    onClick={() => {
                      onEdit(image);
                      setShowMenu(false);
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    Edit
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={() => {
                      onDelete(image.id);
                      setShowMenu(false);
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return null;
}
