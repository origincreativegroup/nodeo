import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface ImageData {
  id: number
  filename: string
  current_filename: string
  file_path: string
  file_size: number
  mime_type: string
  width?: number
  height?: number
  ai_description?: string
  ai_tags?: string[]
  ai_objects?: string[]
  ai_scene?: string
  analyzed_at?: string
  created_at?: string
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
  settings: Settings
  updateSettings: (updates: Partial<Settings>) => void
  selectedImageIds: number[]
  toggleImageSelection: (id: number) => void
  clearSelection: () => void
  selectAll: () => void
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
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [selectedImageIds, setSelectedImageIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)

  // Load images on mount
  useEffect(() => {
    const loadImages = async () => {
      try {
        const response = await fetch('/api/images')
        if (response.ok) {
          const data = await response.json()
          setImages(data.images || [])
        }
      } catch (error) {
        console.error('Failed to load images:', error)
      } finally {
        setLoading(false)
      }
    }
    loadImages()
  }, [])

  const addImages = (newImages: ImageData[]) => {
    setImages((prev) => [...prev, ...newImages])
  }

  const removeImage = (id: number) => {
    setImages((prev) => prev.filter((img) => img.id !== id))
    setSelectedImageIds((prev) => prev.filter((imgId) => imgId !== id))
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

  const selectAll = () => {
    setSelectedImageIds(images.map((img) => img.id))
  }

  return (
    <AppContext.Provider
      value={{
        images,
        setImages,
        addImages,
        removeImage,
        updateImage,
        settings,
        updateSettings,
        selectedImageIds,
        toggleImageSelection,
        clearSelection,
        selectAll,
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
