import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AppProvider } from './context/AppContext'
import Navigation from './components/Navigation'
import Dashboard from './pages/Dashboard'
import ImageGallery from './pages/ImageGallery'
import RenameManager from './pages/RenameManager'
import StorageManager from './pages/StorageManager'
import Settings from './pages/Settings'
import FloatingFeedbackButton from './components/FloatingFeedbackButton'

function App() {
  return (
    <AppProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navigation />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/gallery" element={<ImageGallery />} />
            <Route path="/rename" element={<RenameManager />} />
            <Route path="/storage" element={<StorageManager />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
          <Toaster position="top-right" />
          <FloatingFeedbackButton />
        </div>
      </Router>
    </AppProvider>
  )
}

export default App
