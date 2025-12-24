import { useState, useEffect, useRef, useCallback } from 'react'
import { Mic, MicOff, Send, Loader2, Volume2, Square } from 'lucide-react'
import { api } from '../services/api'
import { wsService } from '../services/websocket'
import { useToast } from '../contexts/ToastContext'
import clsx from 'clsx'
import VoiceWaveform from '../components/VoiceWaveform'

export default function Voice() {
  const toast = useToast()
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [response, setResponse] = useState('')
  const [textInput, setTextInput] = useState('')
  const [audioLevel, setAudioLevel] = useState(0)
  const [conversation, setConversation] = useState([])
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const analyserRef = useRef(null)
  const animationRef = useRef(null)
  const conversationEndRef = useRef(null)
  
  // Scroll to bottom of conversation
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])
  
  // Listen for WebSocket responses
  useEffect(() => {
    const unsubChunk = wsService.on('response_chunk', (data) => {
      setResponse(prev => prev + (data.chunk || ''))
    })
    
    const unsubComplete = wsService.on('response_complete', (data) => {
      setIsProcessing(false)
      setResponse('')
      
      if (data.response) {
        setConversation(prev => [...prev, {
          type: 'assistant',
          text: data.response,
          timestamp: new Date(),
        }])
      }
    })
    
    return () => {
      unsubChunk()
      unsubComplete()
    }
  }, [])
  
  // Start recording
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      })
      
      // Setup audio analyser for visualization
      const audioContext = new AudioContext()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser
      
      // Start level monitoring
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const updateLevel = () => {
        if (!isRecording) return
        analyser.getByteFrequencyData(dataArray)
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length
        setAudioLevel(average / 255)
        animationRef.current = requestAnimationFrame(updateLevel)
      }
      
      // Setup media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      })
      
      audioChunksRef.current = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        // Stop level monitoring
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current)
        }
        setAudioLevel(0)
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
        
        // Process audio
        if (audioChunksRef.current.length > 0) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
          await processAudio(audioBlob)
        }
      }
      
      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start(250) // Collect data every 250ms
      setIsRecording(true)
      updateLevel()
      
      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate(50)
      }
      
    } catch (error) {
      console.error('Failed to start recording:', error)
      toast.error('Microphone access denied')
    }
  }, [isRecording, toast])
  
  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate([50, 50, 50])
      }
    }
  }, [isRecording])
  
  // Process recorded audio
  const processAudio = async (audioBlob) => {
    setIsProcessing(true)
    setTranscript('')
    
    try {
      // Transcribe audio
      const result = await api.voice.transcribe(audioBlob)
      
      if (result.text) {
        setTranscript(result.text)
        
        // Add to conversation
        setConversation(prev => [...prev, {
          type: 'user',
          text: result.text,
          timestamp: new Date(),
        }])
        
        // Send command via WebSocket for streaming response
        if (wsService.isConnected) {
          wsService.sendCommand(result.text)
        } else {
          // Fallback to REST API
          const response = await api.commands.send(result.text)
          setConversation(prev => [...prev, {
            type: 'assistant',
            text: response.response,
            timestamp: new Date(),
          }])
          setIsProcessing(false)
        }
      } else {
        toast.warning('Could not understand audio')
        setIsProcessing(false)
      }
    } catch (error) {
      console.error('Audio processing error:', error)
      toast.error('Failed to process audio')
      setIsProcessing(false)
    }
  }
  
  // Send text command
  const sendTextCommand = async () => {
    if (!textInput.trim()) return
    
    const text = textInput.trim()
    setTextInput('')
    setIsProcessing(true)
    
    // Add to conversation
    setConversation(prev => [...prev, {
      type: 'user',
      text,
      timestamp: new Date(),
    }])
    
    try {
      if (wsService.isConnected) {
        wsService.sendCommand(text)
      } else {
        const response = await api.commands.send(text)
        setConversation(prev => [...prev, {
          type: 'assistant',
          text: response.response,
          timestamp: new Date(),
        }])
        setIsProcessing(false)
      }
    } catch (error) {
      toast.error(error.message)
      setIsProcessing(false)
    }
  }
  
  // Handle voice button press
  const handleVoiceButton = () => {
    if (isRecording) {
      stopRecording()
    } else if (!isProcessing) {
      startRecording()
    }
  }
  
  return (
    <div className="h-full flex flex-col">
      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {conversation.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8">
            <div className="w-16 h-16 rounded-full bg-jarvis-primary/10 flex items-center justify-center mb-4">
              <Mic className="w-8 h-8 text-jarvis-primary" />
            </div>
            <h3 className="text-lg font-medium text-jarvis-text mb-2">
              Ready to listen
            </h3>
            <p className="text-sm text-jarvis-muted max-w-xs">
              Tap the microphone button to start speaking, or type your message below.
            </p>
          </div>
        ) : (
          <>
            {conversation.map((msg, index) => (
              <div
                key={index}
                className={clsx(
                  'max-w-[85%] p-3 rounded-2xl animate-fade-in',
                  msg.type === 'user'
                    ? 'ml-auto bg-jarvis-primary text-jarvis-bg rounded-br-md'
                    : 'mr-auto bg-jarvis-card border border-jarvis-border rounded-bl-md'
                )}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                <p className={clsx(
                  'text-[10px] mt-1',
                  msg.type === 'user' ? 'text-jarvis-bg/70' : 'text-jarvis-muted'
                )}>
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            ))}
            
            {/* Streaming response */}
            {response && (
              <div className="mr-auto max-w-[85%] p-3 rounded-2xl rounded-bl-md bg-jarvis-card border border-jarvis-border">
                <p className="text-sm whitespace-pre-wrap">{response}</p>
                <span className="inline-block w-2 h-4 bg-jarvis-primary animate-pulse ml-0.5" />
              </div>
            )}
            
            {/* Processing indicator */}
            {isProcessing && !response && (
              <div className="mr-auto flex items-center gap-2 p-3 rounded-2xl rounded-bl-md bg-jarvis-card border border-jarvis-border">
                <Loader2 className="w-4 h-4 animate-spin text-jarvis-primary" />
                <span className="text-sm text-jarvis-muted">Thinking...</span>
              </div>
            )}
            
            <div ref={conversationEndRef} />
          </>
        )}
      </div>
      
      {/* Voice button and input area */}
      <div className="p-4 bg-jarvis-card border-t border-jarvis-border">
        {/* Voice waveform visualization */}
        <div className="flex items-center justify-center mb-4 h-10">
          <VoiceWaveform 
            isListening={isRecording}
            isSpeaking={isProcessing && !!response}
            size="md"
            barCount={7}
          />
        </div>
        
        {/* Voice button */}
        <div className="flex justify-center mb-4">
          <button
            onClick={handleVoiceButton}
            disabled={isProcessing}
            className={clsx(
              'w-20 h-20 rounded-full flex items-center justify-center transition-all',
              'active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed',
              isRecording
                ? 'bg-jarvis-error voice-pulse'
                : 'bg-jarvis-primary hover:bg-jarvis-primary/90'
            )}
          >
            {isRecording ? (
              <Square className="w-8 h-8 text-white" />
            ) : isProcessing ? (
              <Loader2 className="w-8 h-8 text-jarvis-bg animate-spin" />
            ) : (
              <Mic className="w-8 h-8 text-jarvis-bg" />
            )}
          </button>
        </div>
        
        <p className="text-center text-xs text-jarvis-muted mb-4">
          {isRecording ? 'Tap to stop' : isProcessing ? 'Processing...' : 'Tap to speak'}
        </p>
        
        {/* Text input */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendTextCommand()}
            placeholder="Or type a message..."
            disabled={isProcessing}
            className="flex-1 px-4 py-2.5 bg-jarvis-bg border border-jarvis-border rounded-full
                     text-sm text-jarvis-text placeholder-jarvis-muted/50
                     focus:outline-none focus:border-jarvis-primary
                     disabled:opacity-50"
          />
          {/* Toggle between Send and Mic button based on input */}
          {textInput.trim() ? (
            <button
              onClick={sendTextCommand}
              disabled={isProcessing}
              className="p-2.5 bg-jarvis-primary rounded-full
                       disabled:opacity-50 disabled:cursor-not-allowed
                       hover:bg-jarvis-primary/90 active:scale-95 transition-all"
            >
              <Send className="w-5 h-5 text-jarvis-bg" />
            </button>
          ) : (
            <button
              onClick={handleVoiceButton}
              disabled={isProcessing}
              className={clsx(
                'p-2.5 rounded-full transition-all active:scale-95',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                isRecording
                  ? 'bg-jarvis-error'
                  : 'bg-jarvis-primary hover:bg-jarvis-primary/90'
              )}
            >
              {isRecording ? (
                <MicOff className="w-5 h-5 text-white" />
              ) : (
                <Mic className="w-5 h-5 text-jarvis-bg" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
