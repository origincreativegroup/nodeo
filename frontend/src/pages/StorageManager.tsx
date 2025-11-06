import { Link } from 'react-router-dom'
import { ArrowLeft, Cloud } from 'lucide-react'

export default function StorageManager() {
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="text-blue-600 hover:text-blue-800">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-3xl font-bold">Storage Manager</h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <Cloud className="w-12 h-12 text-blue-600 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Nextcloud</h2>
            <p className="text-gray-600 mb-4">
              Organize and sync images with Nextcloud
            </p>
            <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 w-full">
              Configure
            </button>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <Cloud className="w-12 h-12 text-orange-600 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Cloudflare R2</h2>
            <p className="text-gray-600 mb-4">
              Store images in Cloudflare R2 bucket
            </p>
            <button className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 w-full">
              Configure
            </button>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <Cloud className="w-12 h-12 text-purple-600 mb-4" />
            <h2 className="text-xl font-semibold mb-2">Cloudflare Stream</h2>
            <p className="text-gray-600 mb-4">
              Upload videos to Cloudflare Stream
            </p>
            <button className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 w-full">
              Configure
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
