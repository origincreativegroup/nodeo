import { useMemo } from 'react'
import { ImageData } from '../context/AppContext'

export interface ImageFilterOptions {
  searchQuery: string
  analysisStatus: 'all' | 'analyzed' | 'unanalyzed'
  mediaType: 'all' | 'image' | 'video'
  minFileSize?: number // in MB
  maxFileSize?: number // in MB
  minWidth?: number
  minHeight?: number
  tags?: string[]
  sortBy: 'name' | 'date' | 'size' | 'dimensions'
  sortOrder: 'asc' | 'desc'
}

export const defaultFilterOptions: ImageFilterOptions = {
  searchQuery: '',
  analysisStatus: 'all',
  mediaType: 'all',
  sortBy: 'date',
  sortOrder: 'desc',
}

export function useImageFilter(images: ImageData[], options: ImageFilterOptions) {
  const filteredAndSortedImages = useMemo(() => {
    let result = [...images]

    // Filter by search query
    if (options.searchQuery.trim()) {
      const query = options.searchQuery.toLowerCase()
      result = result.filter((img) => {
        const filename = (img.current_filename || img.filename).toLowerCase()
        const description = (img.ai_description || '').toLowerCase()
        const tags = (img.ai_tags || []).join(' ').toLowerCase()
        const scene = (img.ai_scene || '').toLowerCase()

        return (
          filename.includes(query) ||
          description.includes(query) ||
          tags.includes(query) ||
          scene.includes(query)
        )
      })
    }

    // Filter by analysis status
    if (options.analysisStatus === 'analyzed') {
      result = result.filter((img) => Boolean(img.analyzed_at))
    } else if (options.analysisStatus === 'unanalyzed') {
      result = result.filter((img) => !img.analyzed_at)
    }

    // Filter by media type
    if (options.mediaType === 'image') {
      result = result.filter((img) => img.media_type === 'image' || img.mime_type?.startsWith('image/'))
    } else if (options.mediaType === 'video') {
      result = result.filter((img) => img.media_type === 'video' || img.mime_type?.startsWith('video/'))
    }

    // Filter by file size
    if (options.minFileSize !== undefined) {
      const minBytes = options.minFileSize * 1024 * 1024
      result = result.filter((img) => img.file_size >= minBytes)
    }
    if (options.maxFileSize !== undefined) {
      const maxBytes = options.maxFileSize * 1024 * 1024
      result = result.filter((img) => img.file_size <= maxBytes)
    }

    // Filter by dimensions
    if (options.minWidth !== undefined) {
      result = result.filter((img) => (img.width || 0) >= options.minWidth!)
    }
    if (options.minHeight !== undefined) {
      result = result.filter((img) => (img.height || 0) >= options.minHeight!)
    }

    // Filter by tags
    if (options.tags && options.tags.length > 0) {
      result = result.filter((img) => {
        const imgTags = (img.ai_tags || []).map((t) => t.toLowerCase())
        return options.tags!.some((tag) => imgTags.includes(tag.toLowerCase()))
      })
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0

      switch (options.sortBy) {
        case 'name':
          comparison = (a.current_filename || a.filename).localeCompare(
            b.current_filename || b.filename
          )
          break
        case 'date':
          const dateA = new Date(a.created_at || 0).getTime()
          const dateB = new Date(b.created_at || 0).getTime()
          comparison = dateA - dateB
          break
        case 'size':
          comparison = a.file_size - b.file_size
          break
        case 'dimensions':
          const areaA = (a.width || 0) * (a.height || 0)
          const areaB = (b.width || 0) * (b.height || 0)
          comparison = areaA - areaB
          break
      }

      return options.sortOrder === 'asc' ? comparison : -comparison
    })

    return result
  }, [images, options])

  const stats = useMemo(() => {
    return {
      total: images.length,
      filtered: filteredAndSortedImages.length,
      analyzed: images.filter((img) => Boolean(img.analyzed_at)).length,
      unanalyzed: images.filter((img) => !img.analyzed_at).length,
      imageCount: images.filter(
        (img) => img.media_type === 'image' || img.mime_type?.startsWith('image/')
      ).length,
      videoCount: images.filter(
        (img) => img.media_type === 'video' || img.mime_type?.startsWith('video/')
      ).length,
    }
  }, [images, filteredAndSortedImages])

  return {
    filteredImages: filteredAndSortedImages,
    stats,
  }
}
