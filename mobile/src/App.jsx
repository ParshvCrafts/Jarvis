import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import ErrorBoundary from './components/ErrorBoundary'
import AppShell from './components/AppShell'
import Login from './pages/Login'
import Home from './pages/Home'
import Voice from './pages/Voice'
import Devices from './pages/Devices'
import Settings from './pages/Settings'
import History from './pages/History'
import Contacts from './pages/Contacts'
import QuickLaunch from './pages/QuickLaunch'

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()
  
  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-jarvis-bg">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-jarvis-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-jarvis-muted">Loading...</p>
        </div>
      </div>
    )
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return children
}

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/voice" element={<Voice />} />
                  <Route path="/devices" element={<Devices />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/contacts" element={<Contacts />} />
                  <Route path="/quicklaunch" element={<QuickLaunch />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
