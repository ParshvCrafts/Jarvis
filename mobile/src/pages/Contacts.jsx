import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Users, Search, Plus, Star, Phone, Mail, Edit2, Trash2,
  ChevronLeft, X, Loader2, User, Check
} from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../contexts/ToastContext'
import clsx from 'clsx'

export default function Contacts() {
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()
  
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingContact, setEditingContact] = useState(null)
  
  // Fetch contacts
  const { data: contactsData, isLoading } = useQuery({
    queryKey: ['contacts', categoryFilter, searchQuery],
    queryFn: () => api.contacts.list(categoryFilter || null, searchQuery || null),
  })
  
  // Fetch contact stats
  const { data: stats } = useQuery({
    queryKey: ['contactStats'],
    queryFn: () => api.contacts.count(),
  })
  
  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (contactId) => api.contacts.delete(contactId),
    onSuccess: () => {
      queryClient.invalidateQueries(['contacts'])
      queryClient.invalidateQueries(['contactStats'])
      toast.success('Contact deleted')
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  // Toggle favorite mutation
  const favoriteMutation = useMutation({
    mutationFn: (contactId) => api.contacts.toggleFavorite(contactId),
    onSuccess: () => {
      queryClient.invalidateQueries(['contacts'])
      queryClient.invalidateQueries(['contactStats'])
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
  
  const handleDelete = (contact) => {
    if (confirm(`Delete ${contact.name}?`)) {
      deleteMutation.mutate(contact.id)
    }
  }
  
  const contacts = contactsData?.contacts || []
  const categories = ['family', 'friend', 'work', 'other']
  
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
            <h1 className="text-xl font-semibold text-jarvis-text">Contacts</h1>
            <p className="text-sm text-jarvis-muted">
              {stats?.total || 0} contacts • {stats?.favorites || 0} favorites
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="p-2 bg-jarvis-primary rounded-lg hover:bg-jarvis-primary/80 transition-colors"
          >
            <Plus className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-jarvis-muted" />
          <input
            type="text"
            placeholder="Search contacts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-jarvis-card border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
          />
        </div>
        
        {/* Category filter */}
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          <button
            onClick={() => setCategoryFilter('')}
            className={clsx(
              'px-3 py-1 rounded-full text-sm whitespace-nowrap transition-colors',
              !categoryFilter
                ? 'bg-jarvis-primary text-white'
                : 'bg-jarvis-card text-jarvis-muted hover:bg-jarvis-border'
            )}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={clsx(
                'px-3 py-1 rounded-full text-sm capitalize whitespace-nowrap transition-colors',
                categoryFilter === cat
                  ? 'bg-jarvis-primary text-white'
                  : 'bg-jarvis-card text-jarvis-muted hover:bg-jarvis-border'
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>
      
      {/* Contact list */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-jarvis-primary" />
          </div>
        ) : contacts.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-jarvis-muted mx-auto mb-3" />
            <p className="text-jarvis-muted">No contacts found</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 px-4 py-2 bg-jarvis-primary text-white rounded-lg hover:bg-jarvis-primary/80 transition-colors"
            >
              Add Contact
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {contacts.map((contact) => (
              <div
                key={contact.id}
                className="bg-jarvis-card rounded-xl border border-jarvis-border p-4"
              >
                <div className="flex items-center gap-3">
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-jarvis-primary/20 flex items-center justify-center flex-shrink-0">
                    <User className="w-6 h-6 text-jarvis-primary" />
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-jarvis-text truncate">
                        {contact.name}
                      </p>
                      {contact.favorite && (
                        <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                      )}
                    </div>
                    {contact.nickname && (
                      <p className="text-xs text-jarvis-muted">"{contact.nickname}"</p>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-sm text-jarvis-muted flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        {contact.phone}
                      </span>
                      {contact.email && (
                        <span className="text-sm text-jarvis-muted flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {contact.email.split('@')[0]}...
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => favoriteMutation.mutate(contact.id)}
                      className="p-2 hover:bg-jarvis-border/50 rounded-lg transition-colors"
                    >
                      <Star className={clsx(
                        'w-4 h-4',
                        contact.favorite 
                          ? 'text-yellow-500 fill-yellow-500' 
                          : 'text-jarvis-muted'
                      )} />
                    </button>
                    <button
                      onClick={() => setEditingContact(contact)}
                      className="p-2 hover:bg-jarvis-border/50 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4 text-jarvis-muted" />
                    </button>
                    <button
                      onClick={() => handleDelete(contact)}
                      className="p-2 hover:bg-jarvis-error/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-jarvis-error" />
                    </button>
                  </div>
                </div>
                
                {/* Category badge */}
                <div className="mt-2">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-jarvis-border text-jarvis-muted capitalize">
                    {contact.category || 'other'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Add/Edit Modal */}
      {(showAddModal || editingContact) && (
        <ContactModal
          contact={editingContact}
          onClose={() => {
            setShowAddModal(false)
            setEditingContact(null)
          }}
        />
      )}
    </div>
  )
}

function ContactModal({ contact, onClose }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const isEditing = !!contact
  
  const [formData, setFormData] = useState({
    name: contact?.name || '',
    phone: contact?.phone || '',
    email: contact?.email || '',
    nickname: contact?.nickname || '',
    category: contact?.category || 'family',
    favorite: contact?.favorite || false,
  })
  
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.name.trim() || !formData.phone.trim()) {
      toast.error('Name and phone are required')
      return
    }
    
    setIsSubmitting(true)
    
    try {
      if (isEditing) {
        await api.contacts.update(contact.id, formData)
        toast.success('Contact updated')
      } else {
        await api.contacts.add(formData)
        toast.success('Contact added')
      }
      queryClient.invalidateQueries(['contacts'])
      queryClient.invalidateQueries(['contactStats'])
      onClose()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const categories = ['family', 'friend', 'work', 'other']
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
      <div className="bg-jarvis-card w-full sm:max-w-md sm:rounded-xl rounded-t-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-jarvis-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-jarvis-text">
            {isEditing ? 'Edit Contact' : 'Add Contact'}
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
              placeholder="John Doe"
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Phone *
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+1 234 567 8900"
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="john@example.com"
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Nickname
            </label>
            <input
              type="text"
              value={formData.nickname}
              onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
              placeholder="Dad, Mom, Bro..."
              className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder-jarvis-muted focus:outline-none focus:border-jarvis-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-jarvis-muted mb-1">
              Category
            </label>
            <div className="flex gap-2 flex-wrap">
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setFormData({ ...formData, category: cat })}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg text-sm capitalize transition-colors',
                    formData.category === cat
                      ? 'bg-jarvis-primary text-white'
                      : 'bg-jarvis-bg border border-jarvis-border text-jarvis-muted hover:border-jarvis-primary'
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <button
              type="button"
              onClick={() => setFormData({ ...formData, favorite: !formData.favorite })}
              className="flex items-center gap-2 text-sm text-jarvis-text"
            >
              <div className={clsx(
                'w-5 h-5 rounded border flex items-center justify-center transition-colors',
                formData.favorite
                  ? 'bg-yellow-500 border-yellow-500'
                  : 'border-jarvis-border'
              )}>
                {formData.favorite && <Check className="w-3 h-3 text-white" />}
              </div>
              <Star className={clsx(
                'w-4 h-4',
                formData.favorite ? 'text-yellow-500' : 'text-jarvis-muted'
              )} />
              Add to favorites
            </button>
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
                  {isEditing ? 'Update' : 'Add'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
