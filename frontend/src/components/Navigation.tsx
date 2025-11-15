import { Link, useLocation } from 'react-router-dom'
import { Image, FileText, Cloud, Settings, Home } from 'lucide-react'

export default function Navigation() {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/gallery', icon: Image, label: 'Gallery' },
    { path: '/rename', icon: FileText, label: 'Rename' },
    { path: '/storage', icon: Cloud, label: 'Storage' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Image className="w-8 h-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">nodeo</span>
          </Link>

          <div className="flex items-center gap-6">
            {navItems.map(({ path, icon: Icon, label }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  isActive(path)
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}
