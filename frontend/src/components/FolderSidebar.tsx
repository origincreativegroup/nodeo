import { useState } from 'react';
import {
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  FolderPlus,
  MoreVertical,
  Edit2,
  Trash2,
  Bot,
  Calendar,
  Briefcase,
  Hash,
} from 'lucide-react';
import Button from './Button';
import { GroupSummary, GroupType } from '../context/AppContext';

interface FolderNode extends GroupSummary {
  parent_id?: number | null;
  sort_order?: number;
  children?: FolderNode[];
}

interface FolderSidebarProps {
  folders: FolderNode[];
  selectedFolderId: number | null;
  onFolderSelect: (id: number | null) => void;
  onFolderCreate?: (name: string, parentId?: number) => void;
  onFolderDelete?: (id: number) => void;
  onFolderRename?: (id: number, newName: string) => void;
  className?: string;
}

export default function FolderSidebar({
  folders,
  selectedFolderId,
  onFolderSelect,
  onFolderCreate,
  onFolderDelete,
  onFolderRename,
  className = '',
}: FolderSidebarProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set());
  const [contextMenuFolder, setContextMenuFolder] = useState<number | null>(null);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');

  const toggleExpand = (folderId: number) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  };

  const handleFolderClick = (folderId: number) => {
    onFolderSelect(folderId);
  };

  const handleCreateFolder = () => {
    if (newFolderName.trim() && onFolderCreate) {
      onFolderCreate(newFolderName.trim());
      setNewFolderName('');
      setIsCreatingFolder(false);
    }
  };

  const handleDeleteFolder = (folderId: number) => {
    if (confirm('Are you sure you want to delete this folder?')) {
      onFolderDelete?.(folderId);
      setContextMenuFolder(null);
    }
  };

  const getFolderIcon = (groupType: GroupType, isExpanded: boolean) => {
    if (isExpanded) {
      return <FolderOpen className="w-4 h-4" />;
    }

    switch (groupType) {
      case 'ai_tag_cluster':
      case 'ai_scene_cluster':
      case 'ai_embedding_cluster':
      case 'ai_project_cluster':
        return <Bot className="w-4 h-4 text-blue-600" />;
      case 'upload_batch':
        return <Calendar className="w-4 h-4 text-purple-600" />;
      case 'manual_collection':
        return <Folder className="w-4 h-4 text-gray-600" />;
      default:
        return <Folder className="w-4 h-4" />;
    }
  };

  const getGroupTypeLabel = (groupType: GroupType): string => {
    switch (groupType) {
      case 'ai_tag_cluster':
        return 'Tags';
      case 'ai_scene_cluster':
        return 'Scenes';
      case 'ai_embedding_cluster':
        return 'Similar';
      case 'ai_project_cluster':
        return 'Projects';
      case 'upload_batch':
        return 'Uploads';
      case 'manual_collection':
        return 'Manual';
      default:
        return 'Folder';
    }
  };

  const renderFolder = (folder: FolderNode, level: number = 0) => {
    const isExpanded = expandedFolders.has(folder.id);
    const isSelected = selectedFolderId === folder.id;
    const hasChildren = folder.children && folder.children.length > 0;

    return (
      <div key={folder.id}>
        <div
          className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-100 transition-colors ${
            isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          }`}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
        >
          {/* Expand/Collapse Arrow */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(folder.id);
              }}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          ) : (
            <div className="w-4" />
          )}

          {/* Folder Icon */}
          <div onClick={() => handleFolderClick(folder.id)} className="flex items-center gap-2 flex-1 min-w-0">
            {getFolderIcon(folder.group_type, isExpanded)}
            <span className="text-sm truncate flex-1">{folder.name}</span>
            <span className="text-xs text-gray-500 flex-shrink-0">
              {folder.image_ids?.length || 0}
            </span>
          </div>

          {/* Context Menu */}
          {folder.is_user_defined && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setContextMenuFolder(contextMenuFolder === folder.id ? null : folder.id);
                }}
                className="p-0.5 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="w-3 h-3" />
              </button>

              {contextMenuFolder === folder.id && (
                <div className="absolute right-0 mt-1 w-32 bg-white rounded-lg shadow-lg border z-20">
                  <button
                    onClick={() => {
                      const newName = prompt('Enter new folder name:', folder.name);
                      if (newName && newName.trim()) {
                        onFolderRename?.(folder.id, newName.trim());
                      }
                      setContextMenuFolder(null);
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Edit2 className="w-3 h-3" />
                    Rename
                  </button>
                  <button
                    onClick={() => handleDeleteFolder(folder.id)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2 text-red-600"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Render Children */}
        {isExpanded && hasChildren && (
          <div>
            {folder.children!.map((child) => renderFolder(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  // Group folders by type
  const manualFolders = folders.filter((f) => f.group_type === 'manual_collection' && !f.parent_id);
  const aiFolders = folders.filter((f) => f.group_type.startsWith('ai_') && !f.parent_id);
  const uploadBatches = folders.filter((f) => f.group_type === 'upload_batch' && !f.parent_id);

  return (
    <div className={`bg-white border-r border-gray-200 overflow-y-auto ${className}`}>
      <div className="p-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Folders</h2>

        {/* All Images */}
        <div
          onClick={() => onFolderSelect(null)}
          className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-100 transition-colors ${
            selectedFolderId === null ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          }`}
        >
          <Folder className="w-4 h-4" />
          <span className="text-sm flex-1">All Images</span>
        </div>
      </div>

      {/* Manual Folders Section */}
      <div className="p-2">
        <div className="flex items-center justify-between px-2 py-1">
          <span className="text-xs font-semibold text-gray-500 uppercase">Manual Folders</span>
          {onFolderCreate && (
            <button
              onClick={() => setIsCreatingFolder(true)}
              className="p-0.5 hover:bg-gray-200 rounded"
              title="Create folder"
            >
              <FolderPlus className="w-3 h-3 text-gray-600" />
            </button>
          )}
        </div>

        {isCreatingFolder && (
          <div className="mt-1 px-2">
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateFolder();
                if (e.key === 'Escape') {
                  setIsCreatingFolder(false);
                  setNewFolderName('');
                }
              }}
              placeholder="Folder name..."
              className="w-full px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
        )}

        <div className="mt-1 space-y-0.5">
          {manualFolders.length === 0 ? (
            <p className="text-xs text-gray-400 px-2 py-1">No folders yet</p>
          ) : (
            manualFolders.map((folder) => renderFolder(folder))
          )}
        </div>
      </div>

      {/* AI Folders Section */}
      {aiFolders.length > 0 && (
        <div className="p-2 border-t border-gray-100">
          <div className="flex items-center gap-1 px-2 py-1">
            <Bot className="w-3 h-3 text-blue-600" />
            <span className="text-xs font-semibold text-gray-500 uppercase">AI Groupings</span>
          </div>
          <div className="mt-1 space-y-0.5">
            {aiFolders.map((folder) => renderFolder(folder))}
          </div>
        </div>
      )}

      {/* Upload Batches Section */}
      {uploadBatches.length > 0 && (
        <div className="p-2 border-t border-gray-100">
          <div className="flex items-center gap-1 px-2 py-1">
            <Calendar className="w-3 h-3 text-purple-600" />
            <span className="text-xs font-semibold text-gray-500 uppercase">Upload Batches</span>
          </div>
          <div className="mt-1 space-y-0.5">
            {uploadBatches.map((folder) => renderFolder(folder))}
          </div>
        </div>
      )}
    </div>
  );
}
