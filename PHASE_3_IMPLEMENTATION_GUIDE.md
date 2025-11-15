# JSPOW v2 - Phase 3 Frontend Implementation Guide

## ✅ Completed Foundation

### Backend (Phases 1 & 2) - 100% Complete
- ✅ Database schema with 5 new tables
- ✅ Folder watcher service with watchdog
- ✅ File processor with AI integration
- ✅ Rename executor with rollback
- ✅ WebSocket support for real-time updates
- ✅ Complete REST API (29 endpoints)
- ✅ Activity logging and stats

### Frontend Foundation - Created
- ✅ Type definitions (`src/types/v2.ts`)
- ✅ API client (`src/services/v2/api.ts`)
- ✅ WebSocket hook (`src/hooks/v2/useWebSocket.ts`)
- ✅ Directory structure prepared

---

## 📋 Remaining Frontend Tasks

### 1. Update App Routing

**File:** `frontend/src/App.tsx`

```tsx
// Add v2 routes
import FolderMonitoring from './pages/v2/FolderMonitoring'
import SuggestionsQueue from './pages/v2/SuggestionsQueue'
import ActivityLog from './pages/v2/ActivityLog'

// In <Routes>:
<Route path="/v2/folders" element={<FolderMonitoring />} />
<Route path="/v2/suggestions" element={<SuggestionsQueue />} />
<Route path="/v2/activity" element={<ActivityLog />} />
```

### 2. Update Navigation

**File:** `frontend/src/components/Navigation.tsx`

```tsx
import { FolderOpen, ListChecks, Activity } from 'lucide-react'

// Add to navItems:
{
  path: '/v2/folders',
  icon: FolderOpen,
  label: 'Auto Monitor',
  badge: 'v2'
},
```

---

## 🎨 Component Implementation Guide

### Page 1: Folder Management (`pages/v2/FolderMonitoring.tsx`)

#### Features
- List all watched folders
- Add new folder with directory picker
- Show real-time progress bars
- Pause/resume/delete actions
- Folder statistics dashboard

#### Key Components
```tsx
<FolderCard
  folder={folder}
  onPause={handlePause}
  onResume={handleResume}
  onRescan={handleRescan}
  onDelete={handleDelete}
/>

<AddFolderDialog
  open={isOpen}
  onAdd={handleAddFolder}
  onClose={() => setIsOpen(false)}
/>

<FolderStats stats={stats} />
```

#### WebSocket Integration
```tsx
const { lastMessage } = useWebSocket('/ws/progress', true)

useEffect(() => {
  if (lastMessage?.type === 'progress_update') {
    updateFolderProgress(lastMessage.folders)
  }
}, [lastMessage])
```

#### API Calls
```tsx
import {
  listWatchedFolders,
  addWatchedFolder,
  updateFolder,
  deleteFolder,
  rescanFolder
} from '../../services/v2/api'
```

---

### Page 2: Suggestions Queue (`pages/v2/SuggestionsQueue.tsx`)

#### Features
- Grid of suggestion cards with thumbnails
- Batch selection (checkboxes)
- Filter by folder/status/confidence
- Sort by date/confidence
- Inline edit suggested names
- Batch approve/reject/execute

#### Key Components
```tsx
<SuggestionCard
  suggestion={suggestion}
  selected={selected.includes(suggestion.id)}
  onSelect={handleSelect}
  onApprove={handleApprove}
  onReject={handleReject}
  onEdit={handleEdit}
/>

<BatchActions
  selectedCount={selected.length}
  onApproveAll={handleBatchApprove}
  onRejectAll={handleBatchReject}
  onExecuteAll={handleBatchExecute}
/>

<FilterBar
  folders={folders}
  onFilterChange={handleFilterChange}
/>
```

#### States
```tsx
const [suggestions, setSuggestions] = useState<RenameSuggestion[]>([])
const [selected, setSelected] = useState<string[]>([])
const [filters, setFilters] = useState({
  folder_id: null,
  status: 'pending',
  min_confidence: 0.5
})
```

---

### Page 3: Activity Log (`pages/v2/ActivityLog.tsx`)

#### Features
- Chronological timeline
- Filter by action type/status/date
- Rollback button for renames
- Export as CSV/JSON
- Search functionality

#### Key Components
```tsx
<ActivityTimeline logs={logs} />

<ActivityItem
  log={log}
  onRollback={handleRollback}
  onRetry={handleRetry}
/>

<ActivityFilters
  onFilterChange={handleFilterChange}
/>

<ExportButton
  onExport={(format) => handleExport(format)}
/>
```

#### Action Icons
```tsx
const actionIcons = {
  rename: <FileText className="text-blue-500" />,
  approve: <Check className="text-green-500" />,
  reject: <X className="text-red-500" />,
  scan: <Search className="text-purple-500" />,
  error: <AlertCircle className="text-red-600" />,
}
```

---

## 🔄 State Management Pattern

### Using React Query (Recommended)

```bash
npm install @tanstack/react-query
```

```tsx
// hooks/v2/useFolders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../../services/v2/api'

export function useFolders() {
  return useQuery({
    queryKey: ['folders'],
    queryFn: api.listWatchedFolders,
    refetchInterval: 5000, // Refetch every 5s
  })
}

export function useAddFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ path, name }: { path: string; name?: string }) =>
      api.addWatchedFolder(path, name),
    onSuccess: () => {
      queryClient.invalidateQueries(['folders'])
    },
  })
}
```

---

## 🎨 UI Component Examples

### Progress Bar with Real-time Updates

```tsx
function FolderProgress({ folder }: { folder: WatchedFolder }) {
  const progress = folder.file_count > 0
    ? Math.round((folder.analyzed_count / folder.file_count) * 100)
    : 0

  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span>{folder.status === 'scanning' ? 'Scanning' : 'Idle'}</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            folder.status === 'scanning' ? 'bg-blue-500' : 'bg-green-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="text-xs text-gray-500 mt-1">
        {folder.analyzed_count} / {folder.file_count} files analyzed
      </div>
    </div>
  )
}
```

### Confidence Score Badge

```tsx
function ConfidenceScore({ score }: { score: number }) {
  const percentage = Math.round(score * 100)
  const color = score >= 0.8 ? 'green' : score >= 0.6 ? 'yellow' : 'red'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
        <div
          className={`bg-${color}-500 h-1.5 rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className={`text-${color}-600 font-medium text-sm`}>
        {percentage}%
      </span>
    </div>
  )
}
```

### Status Indicator

```tsx
function StatusIndicator({ status }: { status: WatchedFolderStatus }) {
  const config = {
    active: { color: 'green', icon: '●', label: 'Active' },
    scanning: { color: 'blue', icon: '◐', label: 'Scanning...' },
    paused: { color: 'yellow', icon: '❚❚', label: 'Paused' },
    error: { color: 'red', icon: '⚠', label: 'Error' },
  }

  const { color, icon, label } = config[status]

  return (
    <div className={`flex items-center gap-2 text-${color}-600`}>
      <span className="text-lg">{icon}</span>
      <span className="font-medium">{label}</span>
    </div>
  )
}
```

---

## 📱 Responsive Design

### Tailwind Breakpoints

```tsx
// Mobile-first approach
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Folder cards */}
</div>

// Hide on mobile, show on tablet+
<span className="hidden sm:inline">Details</span>

// Stack vertically on mobile
<div className="flex flex-col sm:flex-row gap-4">
```

---

## 🔔 Toast Notifications

```tsx
import toast from 'react-hot-toast'

// Success
toast.success('Folder added successfully!')

// Error
toast.error('Failed to add folder')

// Loading
const toastId = toast.loading('Processing...')
// Later:
toast.success('Done!', { id: toastId })

// Custom
toast.custom((t) => (
  <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} ...`}>
    <h4>Rename Complete</h4>
    <p>File renamed to: {newFilename}</p>
  </div>
))
```

---

## 🧪 Testing Checklist

### Folder Management
- [ ] Add folder with valid path
- [ ] Add folder with invalid path (error handling)
- [ ] Real-time progress updates via WebSocket
- [ ] Pause/resume folder
- [ ] Delete folder
- [ ] Rescan folder
- [ ] Show folder stats

### Suggestions Queue
- [ ] List pending suggestions
- [ ] Select/deselect suggestions
- [ ] Approve single suggestion
- [ ] Reject single suggestion
- [ ] Batch approve (select multiple)
- [ ] Batch execute approved suggestions
- [ ] Edit suggested filename
- [ ] Filter by folder/status/confidence
- [ ] Sort by different criteria

### Activity Log
- [ ] List recent activities
- [ ] Filter by action type
- [ ] Filter by status
- [ ] Filter by date range
- [ ] Export as CSV
- [ ] Export as JSON
- [ ] Rollback rename
- [ ] Show error details

### WebSocket
- [ ] Connection established on page load
- [ ] Reconnection after disconnect
- [ ] Real-time folder progress updates
- [ ] Ping/pong keep-alive
- [ ] Connection status indicator

---

## 📦 Required npm Packages

```bash
# Already installed (from existing frontend)
# - react
# - react-router-dom
# - tailwindcss
# - lucide-react
# - react-hot-toast

# New for Phase 3
npm install @tanstack/react-query
```

---

## 🚀 Quick Start Command

```bash
# Frontend development server
cd frontend
npm install
npm run dev

# Backend (in separate terminal)
cd ..
uvicorn main:app --reload --port 8002
```

Access at: `http://localhost:5173`

---

## 📁 Final File Structure

```
frontend/src/
├── pages/v2/
│   ├── FolderMonitoring.tsx        ⭐ Main dashboard
│   ├── SuggestionsQueue.tsx        ⭐ Rename suggestions
│   └── ActivityLog.tsx             ⭐ Activity timeline
│
├── components/v2/
│   ├── folders/
│   │   ├── FolderCard.tsx
│   │   ├── FolderList.tsx
│   │   ├── AddFolderDialog.tsx
│   │   ├── FolderProgress.tsx
│   │   └── FolderStats.tsx
│   │
│   ├── suggestions/
│   │   ├── SuggestionCard.tsx
│   │   ├── SuggestionGrid.tsx
│   │   ├── BatchActions.tsx
│   │   ├── FilterBar.tsx
│   │   └── EditSuggestionDialog.tsx
│   │
│   ├── activity/
│   │   ├── ActivityTimeline.tsx
│   │   ├── ActivityItem.tsx
│   │   ├── ActivityFilters.tsx
│   │   └── ExportDialog.tsx
│   │
│   └── shared/
│       ├── ProgressBar.tsx
│       ├── StatusIndicator.tsx
│       ├── ConfidenceScore.tsx
│       └── ImagePreview.tsx
│
├── hooks/v2/
│   ├── useWebSocket.ts             ✅ Created
│   ├── useFolders.ts               ⏳ TODO
│   ├── useSuggestions.ts           ⏳ TODO
│   └── useActivityLog.ts           ⏳ TODO
│
├── services/v2/
│   └── api.ts                      ✅ Created
│
└── types/
    └── v2.ts                       ✅ Created
```

---

## 🎯 Implementation Priority

### Week 1: Core Infrastructure ✅
- [x] Type definitions
- [x] API client
- [x] WebSocket hook
- [ ] React Query hooks
- [ ] Shared components (ProgressBar, StatusIndicator)

### Week 2: Folder Management
- [ ] FolderMonitoring page
- [ ] FolderCard component
- [ ] AddFolderDialog
- [ ] WebSocket integration
- [ ] Real-time updates

### Week 3: Suggestions Queue
- [ ] SuggestionsQueue page
- [ ] SuggestionCard with thumbnails
- [ ] Batch selection logic
- [ ] FilterBar and sorting
- [ ] Execute workflow

### Week 4: Activity Log & Polish
- [ ] ActivityLog page
- [ ] Timeline component
- [ ] Rollback functionality
- [ ] Export CSV/JSON
- [ ] Final testing and polish

---

## 💡 Pro Tips

### Performance Optimization
```tsx
// Virtualized lists for large datasets
import { useVirtualizer } from '@tanstack/react-virtual'

// Debounced search
import { useDebouncedValue } from '@mantine/hooks'

// Memoized components
const SuggestionCard = memo(({ suggestion }) => { ... })
```

### Error Boundaries
```tsx
class ErrorBoundary extends Component {
  state = { hasError: false }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong.</div>
    }
    return this.props.children
  }
}
```

### Loading States
```tsx
if (isLoading) return <LoadingSpinner />
if (error) return <ErrorDisplay error={error} />
if (!data) return null

return <DataDisplay data={data} />
```

---

## 🎨 Design Tokens (Tailwind Config)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'folder-active': '#10b981',
        'folder-scanning': '#3b82f6',
        'folder-paused': '#f59e0b',
        'folder-error': '#ef4444',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
}
```

---

## 📊 Success Metrics

- [ ] Add folder in < 2 clicks
- [ ] Real-time progress visible within 1 second
- [ ] Batch approve 50+ suggestions in < 2 seconds
- [ ] Activity log scrolls smoothly with 1000+ entries
- [ ] Mobile responsive on tablets
- [ ] WebSocket reconnects automatically
- [ ] No data loss on page refresh (React Query cache)

---

## 🔗 API Integration Examples

### Complete Workflow Example

```tsx
// 1. User adds folder
const addFolderMutation = useAddFolder()
await addFolderMutation.mutateAsync({ path: '/photos', name: 'Vacation' })

// 2. WebSocket receives progress
useEffect(() => {
  if (lastMessage?.folders) {
    // Update local state with real-time progress
  }
}, [lastMessage])

// 3. Suggestions appear
const { data: suggestions } = useSuggestions({ folder_id: folderId })

// 4. User approves
await approveSuggestion(suggestionId)

// 5. User executes
await executeSuggestion(suggestionId, true)

// 6. View in activity log
const { data: activities } = useActivityLog({ days: 7 })
```

---

## ✅ Definition of Done

Phase 3 is complete when:

1. **Folder Management**
   - Can add/remove folders
   - Real-time progress bars update
   - All folder actions work (pause/resume/rescan)
   - Stats dashboard shows correct data

2. **Suggestions Queue**
   - Grid view with thumbnails
   - Batch selection works
   - Can approve/reject/execute
   - Filters and sorting functional

3. **Activity Log**
   - Timeline displays correctly
   - Filters work
   - Export works (CSV & JSON)
   - Rollback works

4. **General**
   - WebSocket connection stable
   - Mobile responsive
   - Error handling throughout
   - Loading states everywhere
   - Toast notifications

---

## 🚢 Deployment Checklist

```bash
# 1. Build frontend
cd frontend
npm run build

# 2. Copy to FastAPI static
cp -r dist/* ../static/

# 3. Test production build
cd ..
uvicorn main:app --host 0.0.0.0 --port 8002

# 4. Docker build
docker-compose build

# 5. Deploy
docker-compose up -d
```

---

**Ready to implement! Start with the hooks and shared components, then build each page incrementally.** 🚀
