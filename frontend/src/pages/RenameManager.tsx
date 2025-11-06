import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function RenameManager() {
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center gap-4 mb-8">
          <Link to="/" className="text-blue-600 hover:text-blue-800">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-3xl font-bold">Rename Manager</h1>
        </div>

        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-xl font-semibold mb-4">Batch Rename</h2>
          <p className="text-gray-600">
            Use custom templates to rename your images based on AI analysis.
          </p>

          <div className="mt-6">
            <label className="block text-sm font-medium mb-2">
              Naming Template
            </label>
            <input
              type="text"
              placeholder="{description}_{date}_{index}"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="mt-4 text-sm text-gray-600">
            <p className="font-medium mb-2">Available variables:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <code className="bg-gray-100 px-2 py-1 rounded">{'{description}'}</code> - AI-generated description
              </li>
              <li>
                <code className="bg-gray-100 px-2 py-1 rounded">{'{tags}'}</code> - Top tags
              </li>
              <li>
                <code className="bg-gray-100 px-2 py-1 rounded">{'{date}'}</code> - Current date
              </li>
              <li>
                <code className="bg-gray-100 px-2 py-1 rounded">{'{index}'}</code> - Sequential index
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
