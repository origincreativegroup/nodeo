import { Link, useLocation } from 'react-router-dom'
import { Image, FileText, Cloud, Settings, Home, FolderSync, Sparkles, History } from 'lucide-react'

export default function Navigation() {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/gallery', icon: Image, label: 'Gallery' },
    { path: '/rename', icon: FileText, label: 'Rename' },
    { path: '/v2/folders', icon: FolderSync, label: 'Auto Monitor', badge: 'v2' },
    { path: '/v2/suggestions', icon: Sparkles, label: 'Suggestions', badge: 'v2' },
    { path: '/v2/activity', icon: History, label: 'Activity', badge: 'v2' },
    { path: '/storage', icon: Cloud, label: 'Storage' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Image className="w-8 h-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">jspow</span>
          </Link>

          <div className="flex items-center gap-6">
            {navItems.map(({ path, icon: Icon, label, badge }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors relative ${
                  isActive(path)
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="hidden sm:inline">{label}</span>
                {badge && (
                  <span className="absolute -top-1 -right-1 px-1.5 py-0.5 text-xs font-bold bg-blue-500 text-white rounded">
                    {badge}
                  </span>
                )}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}
