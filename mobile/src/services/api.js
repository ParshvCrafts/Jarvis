/**
 * API Service for JARVIS Mobile
 * 
 * Centralized API communication with automatic token handling.
 */

const API_BASE = '/api/v1'
const DEFAULT_TIMEOUT = 30000 // 30 seconds

class ApiService {
  constructor() {
    this.token = null
    this.baseUrl = API_BASE
    this.timeout = DEFAULT_TIMEOUT
  }
  
  setToken(token) {
    this.token = token
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    
    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || this.timeout)
    
    const config = {
      ...options,
      headers,
      signal: controller.signal,
    }
    
    try {
      const response = await fetch(url, config)
      clearTimeout(timeoutId)
      
      // Handle 401 - token expired
      if (response.status === 401) {
        // Could trigger token refresh here
        throw new Error('Unauthorized')
      }
      
      // Handle other errors
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || error.error || `HTTP ${response.status}`)
      }
      
      // Return JSON or empty object
      const text = await response.text()
      return text ? JSON.parse(text) : {}
      
    } catch (error) {
      clearTimeout(timeoutId)
      
      // Handle timeout specifically
      if (error.name === 'AbortError') {
        console.error(`API Timeout [${endpoint}]: Request timed out after ${this.timeout}ms`)
        throw new Error('Request timed out. Please try again.')
      }
      
      console.error(`API Error [${endpoint}]:`, error)
      throw error
    }
  }
  
  get(endpoint) {
    return this.request(endpoint, { method: 'GET' })
  }
  
  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
  
  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }
  
  delete(endpoint, data) {
    return this.request(endpoint, {
      method: 'DELETE',
      body: data ? JSON.stringify(data) : undefined,
    })
  }
  
  // Upload file
  async upload(endpoint, file, fieldName = 'file') {
    const formData = new FormData()
    formData.append(fieldName, file)
    
    const headers = {}
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.error || `HTTP ${response.status}`)
    }
    
    return response.json()
  }
  
  // Auth endpoints
  auth = {
    login: (username, password, deviceName, deviceType) => 
      this.post('/auth/login', { username, password, device_name: deviceName, device_type: deviceType }),
    
    logout: () => 
      this.post('/auth/logout', {}),
    
    refreshToken: (refreshToken) => 
      this.post('/auth/token/refresh', { refresh_token: refreshToken }),
    
    changePassword: (oldPassword, newPassword) => 
      this.post('/auth/password/change', { old_password: oldPassword, new_password: newPassword }),
    
    getDevices: () => 
      this.get('/auth/devices'),
    
    revokeDevice: (deviceId) => 
      this.delete(`/auth/devices/${deviceId}`),
  }
  
  // Command endpoints
  commands = {
    send: (text, context = {}, stream = false) => 
      this.post('/command', { text, context, stream }),
    
    history: (page = 1, pageSize = 20) => 
      this.get(`/command/history?page=${page}&page_size=${pageSize}`),
  }
  
  // Status endpoint
  status = {
    get: () => this.get('/status'),
  }
  
  // Device endpoints
  devices = {
    list: () => 
      this.get('/devices'),
    
    get: (deviceId) => 
      this.get(`/devices/${deviceId}`),
    
    action: (deviceId, action, value = null) => 
      this.post(`/devices/${deviceId}/action`, { action, value }),
  }
  
  // Voice endpoints
  voice = {
    transcribe: (audioBlob) => 
      this.upload('/voice/transcribe', audioBlob, 'file'),
    
    transcribeBase64: (audioBase64, format = 'wav') => 
      this.post(`/voice/transcribe/base64?format=${format}`, { audio_base64: audioBase64 }),
    
    speak: (text, voice = null, speed = 1.0) => {
      const params = new URLSearchParams({ text, speed })
      if (voice) params.append('voice', voice)
      return `${this.baseUrl}/voice/speak?${params}`
    },
    
    speakPost: (text, voice = null, speed = 1.0) => 
      this.post('/voice/speak', { text, voice, speed }),
    
    voices: () => 
      this.get('/voice/voices'),
    
    status: () => 
      this.get('/voice/status'),
  }
  
  // Settings endpoints
  settings = {
    get: () => 
      this.get('/settings'),
    
    update: (settings) => 
      this.put('/settings', settings),
  }
  
  // Cache endpoints
  cache = {
    stats: () => 
      this.get('/cache/stats'),
    
    clear: (cacheType = 'all') => 
      this.delete('/cache', { cache_type: cacheType }),
  }
  
  // Contacts endpoints
  contacts = {
    list: (category = null, search = null) => {
      const params = new URLSearchParams()
      if (category) params.append('category', category)
      if (search) params.append('search', search)
      const query = params.toString()
      return this.get(`/contacts${query ? '?' + query : ''}`)
    },
    
    count: () => 
      this.get('/contacts/count'),
    
    get: (contactId) => 
      this.get(`/contacts/${contactId}`),
    
    add: (contact) => 
      this.post('/contacts', contact),
    
    update: (contactId, contact) => 
      this.put(`/contacts/${contactId}`, contact),
    
    delete: (contactId) => 
      this.delete(`/contacts/${contactId}`),
    
    toggleFavorite: (contactId) => 
      this.post(`/contacts/${contactId}/favorite`),
  }
  
  // Quick Launch endpoints
  quicklaunch = {
    listApps: () => 
      this.get('/quicklaunch/apps'),
    
    addApp: (app) => 
      this.post('/quicklaunch/apps', app),
    
    removeApp: (appName) => 
      this.delete(`/quicklaunch/apps/${encodeURIComponent(appName)}`),
    
    listBookmarks: () => 
      this.get('/quicklaunch/bookmarks'),
    
    addBookmark: (bookmark) => 
      this.post('/quicklaunch/bookmarks', bookmark),
    
    removeBookmark: (bookmarkName) => 
      this.delete(`/quicklaunch/bookmarks/${encodeURIComponent(bookmarkName)}`),
    
    stats: () => 
      this.get('/quicklaunch/stats'),
  }
}

export const api = new ApiService()
