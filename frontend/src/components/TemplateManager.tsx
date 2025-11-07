import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import Button from './Button';

interface Template {
  id: number;
  name: string;
  pattern: string;
  description?: string;
  is_favorite: boolean;
  category: string;
  usage_count: number;
  variables_used: string[];
}

interface TemplateManagerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (pattern: string) => void;
}

export const TemplateManager: React.FC<TemplateManagerProps> = ({
  isOpen,
  onClose,
  onSelectTemplate,
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [predefinedTemplates, setPredefinedTemplates] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    pattern: '',
    description: '',
    category: 'custom',
    is_favorite: false,
  });

  // Available template variables for reference
  const templateVariables = [
    { name: 'Basic Variables', vars: ['description', 'tags', 'scene', 'index', 'original'] },
    { name: 'Date/Time', vars: ['date', 'time', 'datetime', 'year', 'month', 'day', 'hour', 'minute', 'second'] },
    { name: 'Media Metadata', vars: ['width', 'height', 'resolution', 'orientation', 'duration_s', 'frame_rate', 'codec', 'format', 'media_type'] },
    { name: 'File Metadata', vars: ['file_size', 'file_size_kb', 'created_date', 'modified_date', 'extension'] },
    { name: 'AI Analysis', vars: ['primary_color', 'dominant_object', 'mood', 'style'] },
    { name: 'Project', vars: ['project', 'project_name', 'client', 'project_type', 'project_number'] },
    { name: 'Utility', vars: ['random', 'random4', 'uuid'] },
  ];

  const categories = ['all', 'custom', 'basic', 'portfolio', 'media', 'project'];

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen, selectedCategory, showFavoritesOnly]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCategory !== 'all') {
        params.append('category', selectedCategory);
      }
      if (showFavoritesOnly) {
        params.append('favorites_only', 'true');
      }

      const response = await fetch(`/api/templates?${params.toString()}`);
      const data = await response.json();
      setTemplates(data.templates || []);
      setPredefinedTemplates(data.predefined || {});
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    try {
      const response = await fetch('/api/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setFormData({ name: '', pattern: '', description: '', category: 'custom', is_favorite: false });
        loadTemplates();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create template');
      }
    } catch (error) {
      console.error('Failed to create template:', error);
      alert('Failed to create template');
    }
  };

  const handleUpdateTemplate = async (template: Template) => {
    try {
      const response = await fetch(`/api/templates/${template.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(template),
      });

      if (response.ok) {
        setEditingTemplate(null);
        loadTemplates();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to update template');
      }
    } catch (error) {
      console.error('Failed to update template:', error);
      alert('Failed to update template');
    }
  };

  const handleDeleteTemplate = async (templateId: number) => {
    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      const response = await fetch(`/api/templates/${templateId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadTemplates();
      } else {
        alert('Failed to delete template');
      }
    } catch (error) {
      console.error('Failed to delete template:', error);
      alert('Failed to delete template');
    }
  };

  const handleToggleFavorite = async (templateId: number) => {
    try {
      const response = await fetch(`/api/templates/${templateId}/favorite`, {
        method: 'POST',
      });

      if (response.ok) {
        loadTemplates();
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const handleExportTemplates = async () => {
    try {
      const response = await fetch('/api/templates/export');
      const data = await response.json();

      // Download as JSON file
      const blob = new Blob([JSON.stringify(data.templates, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `templates_export_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export templates:', error);
      alert('Failed to export templates');
    }
  };

  const handleImportTemplates = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const templatesData = JSON.parse(text);

      const response = await fetch('/api/templates/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(templatesData),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Imported ${result.imported_count} templates. Errors: ${result.errors.length}`);
        loadTemplates();
      } else {
        alert('Failed to import templates');
      }
    } catch (error) {
      console.error('Failed to import templates:', error);
      alert('Invalid template file format');
    }

    // Reset file input
    event.target.value = '';
  };

  const insertVariable = (variable: string) => {
    const varTag = `{${variable}}`;
    setFormData(prev => ({
      ...prev,
      pattern: prev.pattern + varTag,
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Template Manager">
      <div className="template-manager">
        {/* Header Actions */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex gap-2">
            <Button onClick={() => setShowCreateForm(!showCreateForm)}>
              {showCreateForm ? 'Cancel' : 'New Template'}
            </Button>
            <Button onClick={handleExportTemplates}>Export</Button>
            <label className="btn btn-secondary cursor-pointer">
              Import
              <input
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImportTemplates}
              />
            </label>
          </div>

          <div className="flex gap-2 items-center">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={showFavoritesOnly}
                onChange={(e) => setShowFavoritesOnly(e.target.checked)}
              />
              Favorites Only
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1 border rounded"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Create/Edit Form */}
        {(showCreateForm || editingTemplate) && (
          <div className="bg-gray-50 p-4 rounded-lg mb-4">
            <h3 className="font-semibold mb-3">
              {editingTemplate ? 'Edit Template' : 'Create New Template'}
            </h3>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="Template Name"
                value={editingTemplate ? editingTemplate.name : formData.name}
                onChange={(e) => editingTemplate
                  ? setEditingTemplate({...editingTemplate, name: e.target.value})
                  : setFormData({...formData, name: e.target.value})
                }
                className="w-full px-3 py-2 border rounded"
              />

              <input
                type="text"
                placeholder="Pattern (e.g., {description}_{date})"
                value={editingTemplate ? editingTemplate.pattern : formData.pattern}
                onChange={(e) => editingTemplate
                  ? setEditingTemplate({...editingTemplate, pattern: e.target.value})
                  : setFormData({...formData, pattern: e.target.value})
                }
                className="w-full px-3 py-2 border rounded font-mono"
              />

              <textarea
                placeholder="Description (optional)"
                value={editingTemplate ? editingTemplate.description || '' : formData.description}
                onChange={(e) => editingTemplate
                  ? setEditingTemplate({...editingTemplate, description: e.target.value})
                  : setFormData({...formData, description: e.target.value})
                }
                className="w-full px-3 py-2 border rounded"
                rows={2}
              />

              <select
                value={editingTemplate ? editingTemplate.category : formData.category}
                onChange={(e) => editingTemplate
                  ? setEditingTemplate({...editingTemplate, category: e.target.value})
                  : setFormData({...formData, category: e.target.value})
                }
                className="w-full px-3 py-2 border rounded"
              >
                {categories.filter(c => c !== 'all').map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>

              {/* Quick Variable Insert */}
              <div className="border-t pt-3">
                <p className="text-sm font-semibold mb-2">Quick Insert Variables:</p>
                <div className="max-h-40 overflow-y-auto">
                  {templateVariables.map(group => (
                    <div key={group.name} className="mb-2">
                      <p className="text-xs text-gray-600 mb-1">{group.name}</p>
                      <div className="flex flex-wrap gap-1">
                        {group.vars.map(v => (
                          <button
                            key={v}
                            onClick={() => insertVariable(v)}
                            className="text-xs px-2 py-1 bg-blue-100 hover:bg-blue-200 rounded"
                            type="button"
                          >
                            {v}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={editingTemplate ? () => handleUpdateTemplate(editingTemplate) : handleCreateTemplate}>
                  {editingTemplate ? 'Update' : 'Create'}
                </Button>
                <Button onClick={() => {
                  setEditingTemplate(null);
                  setShowCreateForm(false);
                }}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Templates List */}
        {loading ? (
          <div className="text-center py-8">Loading templates...</div>
        ) : (
          <div className="space-y-2">
            {/* Predefined Templates */}
            {selectedCategory === 'all' && !showFavoritesOnly && (
              <div className="mb-4">
                <h3 className="font-semibold mb-2">Predefined Templates</h3>
                {Object.entries(predefinedTemplates).map(([name, pattern]) => (
                  <div key={name} className="flex items-center justify-between p-3 bg-blue-50 rounded hover:bg-blue-100">
                    <div>
                      <div className="font-medium">{name}</div>
                      <div className="text-sm font-mono text-gray-600">{pattern}</div>
                    </div>
                    <Button onClick={() => onSelectTemplate(pattern)}>Use</Button>
                  </div>
                ))}
              </div>
            )}

            {/* Custom Templates */}
            {templates.length > 0 && (
              <>
                <h3 className="font-semibold mb-2">
                  {showFavoritesOnly ? 'Favorite Templates' : 'Custom Templates'}
                </h3>
                {templates.map(template => (
                  <div key={template.id} className="flex items-center justify-between p-3 bg-white border rounded hover:bg-gray-50">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{template.name}</span>
                        <span className="text-xs px-2 py-0.5 bg-gray-200 rounded">{template.category}</span>
                        {template.usage_count > 0 && (
                          <span className="text-xs text-gray-500">Used {template.usage_count}x</span>
                        )}
                      </div>
                      <div className="text-sm font-mono text-gray-600">{template.pattern}</div>
                      {template.description && (
                        <div className="text-sm text-gray-500 mt-1">{template.description}</div>
                      )}
                    </div>
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleToggleFavorite(template.id)}
                        className={`text-xl ${template.is_favorite ? 'text-yellow-500' : 'text-gray-300'}`}
                        title={template.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                      >
                        ★
                      </button>
                      <Button onClick={() => onSelectTemplate(template.pattern)}>Use</Button>
                      <Button onClick={() => setEditingTemplate(template)}>Edit</Button>
                      <Button onClick={() => handleDeleteTemplate(template.id)} variant="danger">
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </>
            )}

            {templates.length === 0 && selectedCategory === 'all' && !showFavoritesOnly && (
              <div className="text-center py-8 text-gray-500">
                No custom templates yet. Create one to get started!
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};
