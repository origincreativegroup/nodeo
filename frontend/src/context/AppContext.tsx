import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'

export type GroupType =
  | 'ai_tag_cluster'
  | 'ai_scene_cluster'
  | 'ai_embedding_cluster'
  | 'manual_collection'
  | 'upload_batch'

export interface ImageGroupRef {
  id: number
  name: string
  group_type: GroupType
}

export interface UploadBatchRef {
  id: number
  label?: string
}

export interface GroupSummary {
  id: number
  name: string
  group_type: GroupType
  description?: string | null
  metadata?: Record<string, unknown>
  image_ids: number[]
  is_user_defined?: boolean
  created_by?: string | null
  created_at?: string | null
}

export interface ImageData {
  id: number
  filename: string
  current_filename: string
  file_path: string
  file_size: number
  mime_type: string
  media_type?: string
  width?: number
  height?: number
  duration_s?: number
  frame_rate?: number
  codec?: string
  format?: string
  metadata_id?: number
  ai_description?: string
  ai_tags?: string[]
  ai_objects?: string[]
  ai_scene?: string
  ai_embedding?: number[]
  analyzed_at?: string
  created_at?: string
  groups?: ImageGroupRef[]
  upload_batch?: UploadBatchRef | null
  metadata_sidecar_exists?: boolean
  // Smart Rename fields
  suggested_filename?: string
  filename_accepted?: boolean
  last_renamed_at?: string
}

export interface Settings {
  ollamaHost: string
  ollamaModel: string
  nextcloudUrl: string
  nextcloudUsername: string
  nextcloudPassword: string
  nextcloudEnabled: boolean
  cloudflareR2AccountId: string
  cloudflareR2AccessKeyId: string
  cloudflareR2SecretAccessKey: string
  cloudflareR2Bucket: string
  cloudflareR2Enabled: boolean
  cloudflareStreamApiToken: string
  cloudflareStreamEnabled: boolean
}

interface AppContextType {
  images: ImageData[]
  setImages: (images: ImageData[]) => void
  addImages: (newImages: ImageData[]) => void
  removeImage: (id: number) => void
  updateImage: (id: number, updates: Partial<ImageData>) => void
  groups: GroupSummary[]
  refreshGroups: () => Promise<void>
  settings: Settings
  updateSettings: (updates: Partial<Settings>) => void
  selectedImageIds: number[]
  toggleImageSelection: (id: number) => void
  clearSelection: () => void
  selectAll: (ids?: number[]) => void
  selectImageIds: (ids: number[]) => void
  activeGroupFilter: number | null
  setActiveGroupFilter: (groupId: number | null) => void
  bulkUpdateTags: (
    imageIds: number[],
    tags: string[],
    operation?: 'replace' | 'add' | 'remove'
  ) => Promise<void>
}

const AppContext = createContext<AppContextType | undefined>(undefined)

const defaultSettings: Settings = {
  ollamaHost: 'http://192.168.50.248:11434',
  ollamaModel: 'llava',
  nextcloudUrl: 'https://nextcloud.lan',
  nextcloudUsername: 'admin',
  nextcloudPassword: '',
  nextcloudEnabled: false,
  cloudflareR2AccountId: '',
  cloudflareR2AccessKeyId: '',
  cloudflareR2SecretAccessKey: '',
  cloudflareR2Bucket: '',
  cloudflareR2Enabled: false,
  cloudflareStreamApiToken: '',
  cloudflareStreamEnabled: false,
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [images, setImages] = useState<ImageData[]>([])
  const [groups, setGroups] = useState<GroupSummary[]>([])
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [selectedImageIds, setSelectedImageIds] = useState<number[]>([])
  const [activeGroupFilter, setActiveGroupFilter] = useState<number | null>(null)

  const loadImages = useCallback(async () => {
    try {
      const response = await fetch('/api/images')
      if (response.ok) {
        const data = await response.json()
        setImages(data.images || [])
      }
    } catch (error) {
      console.error('Failed to load images:', error)
    }
  }, [])

  const refreshGroups = useCallback(async () => {
    try {
      const response = await fetch('/api/groupings')
      if (response.ok) {
        const data = await response.json()
        setGroups(data.groups || [])
      }
    } catch (error) {
      console.error('Failed to load groups:', error)
    }
  }, [])

  // Load images on mount
  useEffect(() => {
    loadImages()
    refreshGroups()
  }, [loadImages, refreshGroups])

  const addImages = (newImages: ImageData[]) => {
    setImages((prev) => [...prev, ...newImages])
    refreshGroups().catch(() => undefined)
  }

  const removeImage = (id: number) => {
    setImages((prev) => prev.filter((img) => img.id !== id))
    setSelectedImageIds((prev) => prev.filter((imgId) => imgId !== id))
    refreshGroups().catch(() => undefined)
  }

  const updateImage = (id: number, updates: Partial<ImageData>) => {
    setImages((prev) =>
      prev.map((img) => (img.id === id ? { ...img, ...updates } : img))
    )
  }

  const updateSettings = (updates: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...updates }))
  }

  const toggleImageSelection = (id: number) => {
    setSelectedImageIds((prev) =>
      prev.includes(id) ? prev.filter((imgId) => imgId !== id) : [...prev, id]
    )
  }

  const clearSelection = () => {
    setSelectedImageIds([])
  }

  const selectAll = (ids?: number[]) => {
    if (ids && ids.length > 0) {
      setSelectedImageIds(Array.from(new Set(ids)))
      return
    }
    setSelectedImageIds(images.map((img) => img.id))
  }

  const selectImageIds = (ids: number[]) => {
    setSelectedImageIds(Array.from(new Set(ids)))
  }

  const bulkUpdateTags = useCallback(
    async (
      imageIds: number[],
      tags: string[],
      operation: 'replace' | 'add' | 'remove' = 'replace'
    ) => {
      if (imageIds.length === 0) {
        return
      }

      try {
        const response = await fetch('/api/images/bulk/tags', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_ids: imageIds, tags, operation }),
        })

        if (!response.ok) {
          throw new Error('Failed to update tags')
        }

        await loadImages()
        await refreshGroups()
      } catch (error) {
        console.error('Failed to update tags in bulk:', error)
        throw error
      }
    },
    [loadImages, refreshGroups]
  )

  return (
    <AppContext.Provider
      value={{
        images,
        setImages,
        addImages,
        removeImage,
        updateImage,
        groups,
        refreshGroups,
        settings,
        updateSettings,
        selectedImageIds,
        toggleImageSelection,
        clearSelection,
        selectAll,
        selectImageIds,
        activeGroupFilter,
        setActiveGroupFilter,
        bulkUpdateTags,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
