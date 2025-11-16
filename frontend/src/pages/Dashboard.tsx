import { Link } from 'react-router-dom'
import { Image, FileText, Cloud, Settings as SettingsIcon } from 'lucide-react'
import { useApp } from '../context/AppContext'

export default function Dashboard() {
  const { images } = useApp()

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-12">
        {/* Hero images */}
        <section className="mb-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <img
                src="https://media.jpstas.com/portfolio/images/motion-hero-chomp-1920x1440.png"
                alt="Motion graphic hero"
                className="w-full h-64 md:h-80 lg:h-96 object-cover"
                loading="eager"
                decoding="async"
                fetchpriority="high"
                referrerPolicy="no-referrer"
              />
            </div>
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <img
                src="https://media.jpstas.com/portfolio/images/heroes/brand-evolution-hero.png"
                alt="Brand Evolution hero"
                className="w-full h-64 md:h-80 lg:h-96 object-cover"
                loading="eager"
                decoding="async"
                referrerPolicy="no-referrer"
              />
            </div>
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <img
                src="https://media.jpstas.com/portfolio/images/heroes/generative-ai-hero.png"
                alt="Generative AI hero"
                className="w-full h-64 md:h-80 lg:h-96 object-cover"
                loading="lazy"
                decoding="async"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </section>

        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-3">Welcome to nodeo</h1>
          <p className="text-lg text-gray-600">
            Local-First AI Media Orchestrator for Images, Audio & Video
          </p>
        </header>

        {/* Stats */}
        {images.length > 0 && (
          <div className="max-w-4xl mx-auto mb-8 grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <div className="text-3xl font-bold text-blue-600">{images.length}</div>
              <div className="text-sm text-gray-600">Total Images</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <div className="text-3xl font-bold text-green-600">
                {images.filter(img => img.ai_description).length}
              </div>
              <div className="text-sm text-gray-600">Analyzed</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <div className="text-3xl font-bold text-purple-600">
                {images.filter(img => !img.ai_description).length}
              </div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
          </div>
        )}

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
