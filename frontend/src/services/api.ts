import axios from 'axios'
import { ImageData, Settings } from '../context/AppContext'

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

export interface RenamePreview {
  image_id: number
  current_filename: string
  proposed_filename: string
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

export default api
