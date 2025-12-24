import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Rocket, Search, Plus, AppWindow, Globe, Trash2,
  ChevronLeft, X, Loader2, Check, ExternalLink
} from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../contexts/ToastContext'
import clsx from 'clsx'

export default function QuickLaunch() {
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  
  const [activeTab, setActiveTab] = useState('apps')
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  
  // Fetch apps
  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['quicklaunch-apps'],
    queryFn: () => api.quicklaunch.listApps(),
  })
  
  // Fetch bookmarks
  const { data: bookmarksData, isLoading: bookmarksLoading } = useQuery({
    queryKey: ['quicklaunch-bookmarks'],
    queryFn: () => api.quicklaunch.listBookmarks(),
  })
  
  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['quicklaunch-stats'],
    queryFn: () => api.quicklaunch.stats(),
  })
  
  // Delete app mutation
  const deleteAppMutation = useMutation({
    mutationFn: (appName) => api.quicklaunch.removeApp(appName),
    onSuccess: () => {
      queryClient.invalidateQueries(['quicklaunch-apps'])
      queryClient.invalidateQueries(['quicklaunch-stats'])
      toast.success('Application removed')
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  // Delete bookmark mutation
  const deleteBookmarkMutation = useMutation({
    mutationFn: (bookmarkName) => api.quicklaunch.removeBookmark(bookmarkName),
    onSuccess: () => {
      queryClient.invalidateQueries(['quicklaunch-bookmarks'])
      queryClient.invalidateQueries(['quicklaunch-stats'])
      toast.success('Bookmark removed')
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  const handleDeleteApp = (app) => {
    if (confirm(`Remove ${app.name}?`)) {
      deleteAppMutation.mutate(app.name)
    }
  }
  
  const handleDeleteBookmark = (bookmark) => {
    if (confirm(`Remove ${bookmark.name}?`)) {
      deleteBookmarkMutation.mutate(bookmark.name)
    }
  }
  
  const apps = appsData?.applications || []
  const bookmarks = bookmarksData?.bookmarks || []
  
  // Filter by search
  const filteredApps = apps.filter(app => 
    app.name.toLowerCase().includes(searchQuery.toLowerCase())
  )
  const filteredBookmarks = bookmarks.filter(b => 
    b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.url.toLowerCase().includes(searchQuery.toLowerCase())
  )
  
  const isLoading = activeTab === 'apps' ? appsLoading : bookmarksLoading
  const items = activeTab === 'apps' ? filteredApps : filteredBookmarks
  
  return (
    <div className="h-full flex flex-col bg-jarvis-bg">
      {/* Header */}
      <div className="p-4 border-b border-jarvis-border">
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => navigate('/settings')}
            className="p-2 hover:bg-jarvis-border/50 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-jarvis-muted" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-jarvis-text">Quick Launch</h1>
            <p className="text-sm text-jarvis-muted">
              {stats?.apps_count || 0} apps • {stats?.bookmarks_count || 0} bookmarks
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="p-2 bg-jarvis-primary rounded-lg hover:bg-jarvis-primary/80 transition-colors"
          >
            <Plus className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setActiveTab('apps')}
            className={clsx(
              'flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2',
              activeTab === 'apps'
                ? 'bg-jarvis-primary text-white'
                : 'bg-jarvis-card text-jarvis-muted hover:bg-jarvis-border'
            )}
          >
            <AppWindow className="w-4 h-4" />
            Applications
          </button>
          <button
            onClick={() => setActiveTab('bookmarks')}
            className={clsx(
              'flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2',
              activeTab === 'bookmarks'
                ? 'bg-jarvis-primary text-white'
                : 'bg-jarvis-card text-jarvis-muted hover:bg-jarvis-border'
            )}
          >
            <Globe className="w-4 h-4" />
            Bookmarks
          </button>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-jarvis-muted" />
          <input
            type="text"
            placeholder={`Search ${activeTab}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-jarvis-card border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
          />
        </div>
      </div>
      
      {/* List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-jarvis-primary" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12">
            {activeTab === 'apps' ? (
              <AppWindow className="w-12 h-12 text-jarvis-muted mx-auto mb-3" />
            ) : (
              <Globe className="w-12 h-12 text-jarvis-muted mx-auto mb-3" />
            )}
            <p className="text-jarvis-muted">
              No {activeTab} found
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 px-4 py-2 bg-jarvis-primary text-white rounded-lg hover:bg-jarvis-primary/80 transition-colors"
            >
              Add {activeTab === 'apps' ? 'Application' : 'Bookmark'}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {activeTab === 'apps' ? (
              filteredApps.map((app) => (
                <div
                  key={app.id}
                  className="bg-jarvis-card rounded-xl border border-jarvis-border p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-jarvis-primary/20 flex items-center justify-center flex-shrink-0">
                      <AppWindow className="w-5 h-5 text-jarvis-primary" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-jarvis-text truncate">
                        {app.name}
                      </p>
                      <p className="text-xs text-jarvis-muted truncate">
                        {app.path || 'System application'}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        {app.category && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-jarvis-border text-jarvis-muted">
                            {app.category}
                          </span>
                        )}
                        <span className="text-xs text-jarvis-muted">
                          Used {app.use_count || 0} times
                        </span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleDeleteApp(app)}
                      className="p-2 hover:bg-jarvis-error/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-jarvis-error" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              filteredBookmarks.map((bookmark) => (
                <div
                  key={bookmark.id}
                  className="bg-jarvis-card rounded-xl border border-jarvis-border p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-jarvis-secondary/20 flex items-center justify-center flex-shrink-0">
                      <Globe className="w-5 h-5 text-jarvis-secondary" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-jarvis-text truncate">
                        {bookmark.name}
                      </p>
                      <a 
                        href={bookmark.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-jarvis-primary hover:underline truncate flex items-center gap-1"
                      >
                        {bookmark.url}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                      <div className="flex items-center gap-3 mt-1">
                        {bookmark.category && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-jarvis-border text-jarvis-muted">
                            {bookmark.category}
                          </span>
                        )}
                        <span className="text-xs text-jarvis-muted">
                          Used {bookmark.use_count || 0} times
                        </span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleDeleteBookmark(bookmark)}
                      className="p-2 hover:bg-jarvis-error/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-jarvis-error" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
      
      {/* Add Modal */}
      {showAddModal && (
        <AddModal
          type={activeTab}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  )
}

function AddModal({ type, onClose }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const isApp = type === 'apps'
  
  const [formData, setFormData] = useState({
    name: '',
    path: '',
    url: '',
    category: '',
  })
  
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.name.trim()) {
      toast.error('Name is required')
      return
    }
    
    if (!isApp && !formData.url.trim()) {
      toast.error('URL is required')
      return
    }
    
    setIsSubmitting(true)
    
    try {
      if (isApp) {
        await api.quicklaunch.addApp({
          name: formData.name,
          path: formData.path || null,
          category: formData.category || null,
        })
        toast.success('Application added')
        queryClient.invalidateQueries(['quicklaunch-apps'])
      } else {
        await api.quicklaunch.addBookmark({
          name: formData.name,
          url: formData.url,
          category: formData.category || null,
        })
        toast.success('Bookmark added')
        queryClient.invalidateQueries(['quicklaunch-bookmarks'])
      }
      queryClient.invalidateQueries(['quicklaunch-stats'])
      onClose()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
      <div className="bg-jarvis-card w-full sm:max-w-md sm:rounded-xl rounded-t-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-jarvis-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-jarvis-text">
            Add {isApp ? 'Application' : 'Bookmark'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-jarvis-border/50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-jarvis-muted" />
          </button>
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder={isApp ? "VS Code" : "GitHub"}
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          {isApp ? (
            <div>
              <label className="block text-sm font-medium text-jarvis-muted mb-1">
                Path (optional)
              </label>
              <input
                type="text"
                value={formData.path}
                onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                placeholder="C:\Program Files\..."
                className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
              />
              <p className="text-xs text-jarvis-muted mt-1">
                Leave empty for system apps (e.g., notepad, calculator)
              </p>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-jarvis-muted mb-1">
                URL *
              </label>
              <input
                type="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="https://github.com"
                className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Category (optional)
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              placeholder="development, social, productivity..."
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          {/* Submit */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-jarvis-border rounded-lg text-jarvis-muted hover:bg-jarvis-border/50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-jarvis-primary text-white rounded-lg hover:bg-jarvis-primary/80 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Add
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
