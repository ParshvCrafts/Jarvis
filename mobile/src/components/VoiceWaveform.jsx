/**
 * VoiceWaveform Component
 * 
 * Animated waveform visualization for voice activity.
 * Shows different animations for listening vs speaking states.
 */

import React from 'react';

/**
 * Voice waveform visualization with CSS animations
 * 
 * @param {Object} props
 * @param {boolean} props.isListening - Whether JARVIS is listening
 * @param {boolean} props.isSpeaking - Whether JARVIS is speaking
 * @param {string} props.className - Additional CSS classes
 * @param {number} props.barCount - Number of bars (default: 5)
 * @param {string} props.size - Size variant: 'sm', 'md', 'lg' (default: 'md')
 */
export default function VoiceWaveform({ 
  isListening = false, 
  isSpeaking = false,
  className = '',
  barCount = 5,
  size = 'md',
}) {
  const isActive = isListening || isSpeaking;
  
  // Size configurations
  const sizes = {
    sm: { height: 24, barWidth: 3, gap: 2 },
    md: { height: 40, barWidth: 4, gap: 3 },
    lg: { height: 60, barWidth: 6, gap: 4 },
  };
  
  const { height, barWidth, gap } = sizes[size] || sizes.md;
  
  // Color based on state
  const getBarColor = () => {
    if (isSpeaking) return 'bg-blue-500';
    if (isListening) return 'bg-green-500';
    return 'bg-gray-400';
  };
  
  // Animation class based on state
  const getAnimationClass = (index) => {
    if (!isActive) return '';
    
    // Different animation delays for each bar
    const delays = ['delay-0', 'delay-75', 'delay-150', 'delay-75', 'delay-0'];
    const delay = delays[index % delays.length];
    
    if (isSpeaking) {
      return `animate-waveform-speak ${delay}`;
    }
    if (isListening) {
      return `animate-waveform-listen ${delay}`;
    }
    return '';
  };
  
  return (
    <div 
      className={`flex items-center justify-center ${className}`}
      style={{ height: `${height}px`, gap: `${gap}px` }}
      role="img"
      aria-label={
        isSpeaking ? 'JARVIS is speaking' : 
        isListening ? 'JARVIS is listening' : 
        'Voice inactive'
      }
    >
      {Array.from({ length: barCount }).map((_, index) => (
        <div
          key={index}
          className={`
            rounded-full transition-all duration-150
            ${getBarColor()}
            ${getAnimationClass(index)}
            ${!isActive ? 'opacity-30' : 'opacity-100'}
          `}
          style={{
            width: `${barWidth}px`,
            height: isActive ? `${height * 0.3}px` : `${height * 0.15}px`,
            minHeight: '4px',
          }}
        />
      ))}
      
      {/* Inline styles for animations */}
      <style jsx>{`
        @keyframes waveform-speak {
          0%, 100% {
            height: ${height * 0.2}px;
          }
          50% {
            height: ${height * 0.9}px;
          }
        }
        
        @keyframes waveform-listen {
          0%, 100% {
            height: ${height * 0.3}px;
          }
          50% {
            height: ${height * 0.6}px;
          }
        }
        
        .animate-waveform-speak {
          animation: waveform-speak 0.5s ease-in-out infinite;
        }
        
        .animate-waveform-listen {
          animation: waveform-listen 0.8s ease-in-out infinite;
        }
        
        .delay-0 { animation-delay: 0ms; }
        .delay-75 { animation-delay: 75ms; }
        .delay-150 { animation-delay: 150ms; }
      `}</style>
    </div>
  );
}

/**
 * Circular waveform variant (Siri-style)
 */
export function CircularWaveform({
  isListening = false,
  isSpeaking = false,
  className = '',
  size = 80,
}) {
  const isActive = isListening || isSpeaking;
  
  const getColor = () => {
    if (isSpeaking) return 'rgba(59, 130, 246, 0.6)'; // blue
    if (isListening) return 'rgba(34, 197, 94, 0.6)'; // green
    return 'rgba(156, 163, 175, 0.3)'; // gray
  };
  
  return (
    <div 
      className={`relative ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Outer ring */}
      <div
        className={`
          absolute inset-0 rounded-full border-2
          ${isSpeaking ? 'border-blue-500' : isListening ? 'border-green-500' : 'border-gray-400'}
          ${isActive ? 'animate-pulse' : ''}
        `}
      />
      
      {/* Inner glow */}
      {isActive && (
        <>
          <div
            className="absolute inset-2 rounded-full animate-ping"
            style={{ backgroundColor: getColor() }}
          />
          <div
            className="absolute inset-4 rounded-full"
            style={{ backgroundColor: getColor() }}
          />
        </>
      )}
      
      {/* Center dot */}
      <div
        className={`
          absolute rounded-full
          ${isSpeaking ? 'bg-blue-500' : isListening ? 'bg-green-500' : 'bg-gray-400'}
        `}
        style={{
          width: size * 0.3,
          height: size * 0.3,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />
    </div>
  );
}

/**
 * Minimal dot indicator
 */
export function VoiceDot({
  isListening = false,
  isSpeaking = false,
  className = '',
  size = 12,
}) {
  const isActive = isListening || isSpeaking;
  
  return (
    <div
      className={`
        rounded-full transition-all duration-300
        ${isSpeaking ? 'bg-blue-500' : isListening ? 'bg-green-500' : 'bg-gray-400'}
        ${isActive ? 'animate-pulse scale-110' : 'scale-100'}
        ${className}
      `}
      style={{ width: size, height: size }}
      role="status"
      aria-label={
        isSpeaking ? 'Speaking' : 
        isListening ? 'Listening' : 
        'Idle'
      }
    />
  );
}
