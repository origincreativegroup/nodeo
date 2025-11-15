import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppProvider } from './context/AppContext'
import Navigation from './components/Navigation'
import Dashboard from './pages/Dashboard'
import ImageGallery from './pages/ImageGallery'
import RenameManager from './pages/RenameManager'
import StorageManager from './pages/StorageManager'
import Settings from './pages/Settings'
import FloatingFeedbackButton from './components/FloatingFeedbackButton'

// v2 Pages
import FolderMonitoring from './pages/v2/FolderMonitoring'
import SuggestionsQueue from './pages/v2/SuggestionsQueue'
import ActivityLog from './pages/v2/ActivityLog'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
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

              {/* v2 Routes */}
              <Route path="/v2/folders" element={<FolderMonitoring />} />
              <Route path="/v2/suggestions" element={<SuggestionsQueue />} />
              <Route path="/v2/activity" element={<ActivityLog />} />
            </Routes>
            <Toaster position="top-right" />
            <FloatingFeedbackButton />
          </div>
        </Router>
      </AppProvider>
    </QueryClientProvider>
  )
}

export default App
