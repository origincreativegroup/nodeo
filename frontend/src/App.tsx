import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ImageGallery from './pages/ImageGallery'
import RenameManager from './pages/RenameManager'
import StorageManager from './pages/StorageManager'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/gallery" element={<ImageGallery />} />
          <Route path="/rename" element={<RenameManager />} />
          <Route path="/storage" element={<StorageManager />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
