import axios from 'axios'
import { Settings, GroupType } from '../context/AppContext'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface UploadResponse {
  total: number
  succeeded: number
  results: Array<{
    success: boolean
    id?: number
    filename: string
    size?: number
    dimensions?: string
    error?: string
    metadata?: MediaMetadataSummary
  }>
}

export interface AnalysisResponse {
  total: number
  succeeded: number
  results: Array<{
    image_id: number
    success: boolean
    analysis?: {
      description: string
      tags: string[]
      objects: string[]
      scene: string
    }
    error?: string
  }>
}

export interface MediaMetadataSummary {
  media_type?: string
  width?: number
  height?: number
  duration_s?: number
  frame_rate?: number
  codec?: string
  format?: string
  metadata_id?: number
  file_path?: string
  file_mtime?: number
}

export interface RenamePreview {
  image_id: number
  current_filename: string
  proposed_filename: string
  metadata: AssetMetadata
  sidecar_exists: boolean
}

export interface RenameResponse {
  total: number
  succeeded: number
  results: Array<{
    image_id: number
    success: boolean
    old_filename?: string
    new_filename?: string
    error?: string
  }>
}

export interface AssetMetadata {
  title: string
  description: string
  alt_text: string
  tags: string[]
  asset_type?: string
  source?: string
}

// Image operations
export const uploadImages = async (files: FileList): Promise<UploadResponse> => {
  const formData = new FormData()
  Array.from(files).forEach((file) => {
    formData.append('files', file)
  })

  const response = await api.post<UploadResponse>('/images/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

export const analyzeImage = async (imageId: number) => {
  const response = await api.post(`/images/${imageId}/analyze`)
  return response.data
}

export const batchAnalyzeImages = async (
  imageIds: number[]
): Promise<AnalysisResponse> => {
  const response = await api.post<AnalysisResponse>('/images/batch-analyze', imageIds)
  return response.data
}

// Rename operations
export const previewRename = async (
  template: string,
  imageIds: number[]
): Promise<{ template: string; previews: RenamePreview[] }> => {
  const response = await api.post('/rename/preview', { template, image_ids: imageIds })
  return response.data
}

export const applyRename = async (
  template: string,
  imageIds: number[],
  createBackups: boolean = true
): Promise<RenameResponse> => {
  const response = await api.post<RenameResponse>('/rename/apply', {
    template,
    image_ids: imageIds,
    create_backups: createBackups,
  })
  return response.data
}

export interface BulkRenamePattern {
  find: string
  replace: string
  useRegex: boolean
  caseSensitive: boolean
}

export const bulkRenameFiles = async (
  imageIds: number[],
  pattern: BulkRenamePattern,
  createBackups: boolean = true
): Promise<RenameResponse> => {
  const response = await api.post<RenameResponse>('/rename/bulk', {
    image_ids: imageIds,
    find: pattern.find,
    replace: pattern.replace,
    use_regex: pattern.useRegex,
    case_sensitive: pattern.caseSensitive,
    create_backups: createBackups,
  })
  return response.data
}

export interface GroupingRecord {
  id: number
  name: string
  description?: string | null
  group_type: GroupType
  metadata?: Record<string, unknown>
  image_ids: number[]
  is_user_defined?: boolean
  created_by?: string | null
  created_at?: string | null
}

export interface ManualGroupPayload {
  name: string
  description?: string
  image_ids?: number[]
}

export const rebuildGroupings = async () => {
  const response = await api.post<{ success: boolean; groups: GroupingRecord[] }>(
    '/groupings/rebuild'
  )
  return response.data
}

export const createManualCollection = async (payload: ManualGroupPayload) => {
  const response = await api.post<{ success: boolean; group: GroupingRecord }>(
    '/groupings/manual',
    payload
  )
  return response.data
}

export const assignImagesToGroup = async (
  groupId: number,
  imageIds: number[],
  replace: boolean = false
) => {
  const response = await api.post<{ success: boolean; group: GroupingRecord }>(
    `/groupings/${groupId}/assign`,
    { image_ids: imageIds, replace }
  )
  return response.data
}

export const saveMetadataSidecar = async (
  imageId: number,
  metadata: AssetMetadata
) => {
  const response = await api.post(`/metadata/${imageId}/sidecar`, metadata)
  return response.data
}

export const downloadMetadataSidecar = async (imageId: number) => {
  const response = await fetch(`/api/metadata/${imageId}/sidecar`)

  if (!response.ok) {
    throw new Error('Failed to download metadata sidecar')
  }

  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition')
  let filename = `metadata-${imageId}.json`

  if (disposition) {
    const match = disposition.match(/filename="?([^";]+)"?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// Template operations
export const listTemplates = async () => {
  const response = await api.get('/templates')
  return response.data
}

export const createTemplate = async (
  name: string,
  pattern: string,
  description?: string
) => {
  const response = await api.post('/templates', { name, pattern, description })
  return response.data
}

// Settings
export const saveSettings = async (settings: Partial<Settings>) => {
  // This would need a backend endpoint to actually save settings
  // For now, just return success
  return { success: true, settings }
}

export const testOllamaConnection = async (host: string) => {
  try {
    const response = await axios.get(`${host}/api/tags`)
    return { success: true, models: response.data.models }
  } catch (error) {
    return { success: false, error: 'Connection failed' }
  }
}

// Storage operations
export const uploadToNextcloud = async (imageId: number, remotePath: string) => {
  const response = await api.post('/storage/nextcloud/upload', {
    image_id: imageId,
    remote_path: remotePath,
  })
  return response.data
}

export const uploadToR2 = async (imageId: number, key: string) => {
  const response = await api.post('/storage/r2/upload', {
    image_id: imageId,
    key,
  })
  return response.data
}

// Smart Rename operations
export const suggestSmartName = async (
  imageId: number,
  folderId?: number,
  context?: Record<string, any>
) => {
  const response = await api.post(`/images/${imageId}/suggest-name`, {
    folder_id: folderId,
    context: context || {},
  })
  return response.data
}

export const batchSuggestNames = async (
  imageIds: number[],
  folderId?: number,
  context?: Record<string, any>
) => {
  const response = await api.post('/images/batch-suggest-names', {
    image_ids: imageIds,
    folder_id: folderId,
    context: context || {},
  })
  return response.data
}

export const quickRenameImage = async (imageId: number, newFilename: string) => {
  const response = await api.post(`/images/${imageId}/quick-rename`, {
    new_filename: newFilename,
  })
  return response.data
}

// Folder operations
export const listFolders = async (includeChildren: boolean = true) => {
  const response = await api.get('/folders', {
    params: { include_children: includeChildren },
  })
  return response.data
}

export const createFolder = async (
  name: string,
  description?: string,
  parentId?: number,
  imageIds?: number[]
) => {
  const response = await api.post('/folders', {
    name,
    description,
    parent_id: parentId,
    image_ids: imageIds || [],
  })
  return response.data
}

export const updateFolder = async (
  folderId: number,
  updates: {
    name?: string
    description?: string
    parent_id?: number
    sort_order?: number
  }
) => {
  const response = await api.put(`/folders/${folderId}`, updates)
  return response.data
}

export const deleteFolder = async (folderId: number, deleteChildren: boolean = false) => {
  const response = await api.delete(`/folders/${folderId}`, {
    params: { delete_children: deleteChildren },
  })
  return response.data
}

export const addImagesToFolder = async (folderId: number, imageIds: number[]) => {
  const response = await api.post(`/folders/${folderId}/images`, {
    image_ids: imageIds,
  })
  return response.data
}

export const removeImageFromFolder = async (folderId: number, imageId: number) => {
  const response = await api.delete(`/folders/${folderId}/images/${imageId}`)
  return response.data
}

export default api
