import { Link } from 'react-router-dom'
import { Image, FileText, Cloud, Settings as SettingsIcon } from 'lucide-react'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <header className="text-center mb-16">
          <h1 className="text-6xl font-bold text-gray-900 mb-4">jspow</h1>
          <p className="text-xl text-gray-600">
            AI-Powered Image Organization & Renaming
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
          <Link
            to="/gallery"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex flex-col items-center text-center">
              <Image className="w-16 h-16 text-blue-600 mb-4" />
              <h2 className="text-xl font-semibold mb-2">Image Gallery</h2>
              <p className="text-gray-600">
                Upload and analyze images with AI
              </p>
            </div>
          </Link>

          <Link
            to="/rename"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex flex-col items-center text-center">
              <FileText className="w-16 h-16 text-green-600 mb-4" />
              <h2 className="text-xl font-semibold mb-2">Rename Manager</h2>
              <p className="text-gray-600">
                Batch rename with custom templates
              </p>
            </div>
          </Link>

          <Link
            to="/storage"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex flex-col items-center text-center">
              <Cloud className="w-16 h-16 text-purple-600 mb-4" />
              <h2 className="text-xl font-semibold mb-2">Storage Manager</h2>
              <p className="text-gray-600">
                Nextcloud, R2, and Stream integration
              </p>
            </div>
          </Link>

          <Link
            to="/settings"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex flex-col items-center text-center">
              <SettingsIcon className="w-16 h-16 text-orange-600 mb-4" />
              <h2 className="text-xl font-semibold mb-2">Settings</h2>
              <p className="text-gray-600">
                Configure integrations and templates
              </p>
            </div>
          </Link>
        </div>

        <div className="mt-16 text-center text-gray-500">
          <p>Powered by LLaVA AI on Ollama</p>
        </div>
      </div>
    </div>
  )
}
