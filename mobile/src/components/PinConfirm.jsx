import { useState, useRef, useEffect } from 'react'
import { X, Lock, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

/**
 * PIN Confirmation Modal for sensitive actions.
 * 
 * Usage:
 * <PinConfirm
 *   isOpen={showPin}
 *   onClose={() => setShowPin(false)}
 *   onConfirm={(pin) => handleAction(pin)}
 *   title="Unlock Door"
 *   message="Enter PIN to confirm this action"
 *   dangerous={true}
 * />
 */
export default function PinConfirm({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title = 'Confirm Action',
  message = 'Enter your PIN to continue',
  dangerous = false,
  pinLength = 4,
}) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const inputRefs = useRef([])
  
  // Focus first input when opened
  useEffect(() => {
    if (isOpen) {
      setPin('')
      setError('')
      setTimeout(() => inputRefs.current[0]?.focus(), 100)
    }
  }, [isOpen])
  
  // Handle digit input
  const handleDigit = (index, value) => {
    if (!/^\d*$/.test(value)) return
    
    const newPin = pin.split('')
    newPin[index] = value.slice(-1)
    const updatedPin = newPin.join('').slice(0, pinLength)
    setPin(updatedPin)
    setError('')
    
    // Move to next input
    if (value && index < pinLength - 1) {
      inputRefs.current[index + 1]?.focus()
    }
    
    // Auto-submit when complete
    if (updatedPin.length === pinLength) {
      handleSubmit(updatedPin)
    }
  }
  
  // Handle backspace
  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }
  
  // Submit PIN
  const handleSubmit = async (submittedPin) => {
    if (submittedPin.length !== pinLength) {
      setError(`PIN must be ${pinLength} digits`)
      return
    }
    
    setIsLoading(true)
    
    try {
      await onConfirm(submittedPin)
      onClose()
    } catch (err) {
      setError(err.message || 'Invalid PIN')
      setPin('')
      inputRefs.current[0]?.focus()
    } finally {
      setIsLoading(false)
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 animate-fade-in">
      <div className="w-full max-w-sm bg-jarvis-card rounded-2xl border border-jarvis-border overflow-hidden animate-slide-up">
        {/* Header */}
        <div className={clsx(
          'p-4 flex items-center gap-3 border-b border-jarvis-border',
          dangerous ? 'bg-jarvis-error/10' : 'bg-jarvis-primary/10'
        )}>
          <div className={clsx(
            'w-10 h-10 rounded-full flex items-center justify-center',
            dangerous ? 'bg-jarvis-error/20' : 'bg-jarvis-primary/20'
          )}>
            {dangerous ? (
              <AlertTriangle className="w-5 h-5 text-jarvis-error" />
            ) : (
              <Lock className="w-5 h-5 text-jarvis-primary" />
            )}
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-jarvis-text">{title}</h3>
            <p className="text-sm text-jarvis-muted">{message}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-jarvis-border/50"
          >
            <X className="w-5 h-5 text-jarvis-muted" />
          </button>
        </div>
        
        {/* PIN Input */}
        <div className="p-6">
          <div className="flex justify-center gap-3 mb-4">
            {Array.from({ length: pinLength }).map((_, index) => (
              <input
                key={index}
                ref={el => inputRefs.current[index] = el}
                type="password"
                inputMode="numeric"
                maxLength={1}
                value={pin[index] || ''}
                onChange={(e) => handleDigit(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                disabled={isLoading}
                className={clsx(
                  'w-12 h-14 text-center text-2xl font-bold rounded-lg border-2',
                  'bg-jarvis-bg text-jarvis-text',
                  'focus:outline-none focus:border-jarvis-primary',
                  'disabled:opacity-50',
                  error ? 'border-jarvis-error' : 'border-jarvis-border'
                )}
              />
            ))}
          </div>
          
          {/* Error message */}
          {error && (
            <p className="text-center text-sm text-jarvis-error mb-4">{error}</p>
          )}
          
          {/* Loading indicator */}
          {isLoading && (
            <p className="text-center text-sm text-jarvis-muted">Verifying...</p>
          )}
        </div>
        
        {/* Actions */}
        <div className="p-4 pt-0 flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 py-3 rounded-lg border border-jarvis-border text-jarvis-text
                     hover:bg-jarvis-border/30 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => handleSubmit(pin)}
            disabled={pin.length !== pinLength || isLoading}
            className={clsx(
              'flex-1 py-3 rounded-lg font-medium',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              dangerous
                ? 'bg-jarvis-error text-white'
                : 'bg-jarvis-primary text-jarvis-bg'
            )}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Simple confirmation dialog (no PIN).
 */
export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm',
  message = 'Are you sure?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  dangerous = false,
}) {
  const [isLoading, setIsLoading] = useState(false)
  
  const handleConfirm = async () => {
    setIsLoading(true)
    try {
      await onConfirm()
      onClose()
    } catch (err) {
      console.error('Confirm error:', err)
    } finally {
      setIsLoading(false)
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 animate-fade-in">
      <div className="w-full max-w-sm bg-jarvis-card rounded-2xl border border-jarvis-border overflow-hidden animate-slide-up">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-jarvis-text mb-2">{title}</h3>
          <p className="text-jarvis-muted">{message}</p>
        </div>
        
        <div className="p-4 pt-0 flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 py-3 rounded-lg border border-jarvis-border text-jarvis-text
                     hover:bg-jarvis-border/30 disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading}
            className={clsx(
              'flex-1 py-3 rounded-lg font-medium',
              'disabled:opacity-50',
              dangerous
                ? 'bg-jarvis-error text-white'
                : 'bg-jarvis-primary text-jarvis-bg'
            )}
          >
            {isLoading ? 'Loading...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
