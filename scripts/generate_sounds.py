"""
Generate JARVIS audio assets.

Creates startup and notification sounds programmatically.
"""

import struct
import wave
import math
import os
from pathlib import Path


def generate_sine_wave(frequency: float, duration: float, sample_rate: int = 44100, amplitude: float = 0.5) -> list:
    """Generate a sine wave."""
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        samples.append(value)
    return samples


def apply_envelope(samples: list, attack: float = 0.1, decay: float = 0.1, sample_rate: int = 44100) -> list:
    """Apply attack/decay envelope to samples."""
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    
    result = samples.copy()
    
    # Attack
    for i in range(min(attack_samples, len(result))):
        result[i] *= i / attack_samples
    
    # Decay
    for i in range(min(decay_samples, len(result))):
        idx = len(result) - 1 - i
        if idx >= 0:
            result[idx] *= i / decay_samples
    
    return result


def mix_samples(*sample_lists) -> list:
    """Mix multiple sample lists together."""
    max_len = max(len(s) for s in sample_lists)
    result = [0.0] * max_len
    
    for samples in sample_lists:
        for i, s in enumerate(samples):
            result[i] += s
    
    # Normalize
    max_val = max(abs(s) for s in result) if result else 1
    if max_val > 1:
        result = [s / max_val for s in result]
    
    return result


def samples_to_wav(samples: list, filename: str, sample_rate: int = 44100):
    """Write samples to a WAV file."""
    # Convert to 16-bit integers
    int_samples = [int(s * 32767) for s in samples]
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for sample in int_samples:
            # Clamp to valid range
            sample = max(-32768, min(32767, sample))
            wav_file.writeframes(struct.pack('<h', sample))


def generate_startup_sound(output_path: str):
    """
    Generate JARVIS startup sound.
    
    Creates a futuristic "powering up" sound with:
    - Rising frequency sweep
    - Harmonic overtones
    - Smooth envelope
    """
    sample_rate = 44100
    duration = 1.5  # seconds
    
    # Base frequency sweep (rising)
    samples = []
    num_samples = int(sample_rate * duration)
    
    for i in range(num_samples):
        t = i / sample_rate
        progress = t / duration
        
        # Frequency rises from 200Hz to 800Hz
        freq = 200 + (600 * progress * progress)  # Quadratic rise
        
        # Add harmonics for richer sound
        value = 0.4 * math.sin(2 * math.pi * freq * t)  # Fundamental
        value += 0.2 * math.sin(2 * math.pi * freq * 2 * t)  # 2nd harmonic
        value += 0.1 * math.sin(2 * math.pi * freq * 3 * t)  # 3rd harmonic
        
        # Add a high "sparkle" tone at the end
        if progress > 0.7:
            sparkle_amp = (progress - 0.7) / 0.3 * 0.3
            value += sparkle_amp * math.sin(2 * math.pi * 1200 * t)
        
        samples.append(value)
    
    # Apply envelope
    samples = apply_envelope(samples, attack=0.1, decay=0.3, sample_rate=sample_rate)
    
    # Add a final "confirmation" beep
    beep_start = int(1.2 * sample_rate)
    beep_duration = 0.2
    beep_samples = generate_sine_wave(880, beep_duration, sample_rate, 0.3)
    beep_samples = apply_envelope(beep_samples, attack=0.02, decay=0.1, sample_rate=sample_rate)
    
    # Extend samples if needed
    total_length = beep_start + len(beep_samples)
    while len(samples) < total_length:
        samples.append(0)
    
    # Mix in the beep
    for i, s in enumerate(beep_samples):
        samples[beep_start + i] += s
    
    # Normalize
    max_val = max(abs(s) for s in samples)
    if max_val > 0:
        samples = [s / max_val * 0.8 for s in samples]
    
    samples_to_wav(samples, output_path, sample_rate)
    print(f"Generated: {output_path}")


def generate_ready_sound(output_path: str):
    """Generate a short 'ready' notification sound."""
    sample_rate = 44100
    
    # Two-tone chime
    tone1 = generate_sine_wave(660, 0.15, sample_rate, 0.5)
    tone1 = apply_envelope(tone1, attack=0.01, decay=0.1, sample_rate=sample_rate)
    
    # Pad between tones
    gap = [0.0] * int(0.05 * sample_rate)
    
    tone2 = generate_sine_wave(880, 0.2, sample_rate, 0.5)
    tone2 = apply_envelope(tone2, attack=0.01, decay=0.15, sample_rate=sample_rate)
    
    samples = tone1 + gap + tone2
    
    samples_to_wav(samples, output_path, sample_rate)
    print(f"Generated: {output_path}")


def generate_success_sound(output_path: str):
    """Generate a success notification sound."""
    sample_rate = 44100
    
    # Rising two-tone
    tone1 = generate_sine_wave(523, 0.1, sample_rate, 0.4)  # C5
    tone1 = apply_envelope(tone1, attack=0.01, decay=0.05, sample_rate=sample_rate)
    
    tone2 = generate_sine_wave(659, 0.15, sample_rate, 0.4)  # E5
    tone2 = apply_envelope(tone2, attack=0.01, decay=0.1, sample_rate=sample_rate)
    
    samples = tone1 + tone2
    
    samples_to_wav(samples, output_path, sample_rate)
    print(f"Generated: {output_path}")


def generate_error_sound(output_path: str):
    """Generate an error notification sound."""
    sample_rate = 44100
    
    # Descending tone
    tone = generate_sine_wave(400, 0.3, sample_rate, 0.4)
    
    # Apply pitch bend down
    for i in range(len(tone)):
        progress = i / len(tone)
        freq = 400 * (1 - 0.3 * progress)  # Descend
        t = i / sample_rate
        tone[i] = 0.4 * math.sin(2 * math.pi * freq * t)
    
    tone = apply_envelope(tone, attack=0.01, decay=0.2, sample_rate=sample_rate)
    
    samples_to_wav(tone, output_path, sample_rate)
    print(f"Generated: {output_path}")


def main():
    """Generate all JARVIS audio assets."""
    # Get assets directory
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / "assets" / "audio"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating JARVIS audio assets...")
    print(f"Output directory: {assets_dir}")
    print()
    
    # Generate sounds
    generate_startup_sound(str(assets_dir / "startup.wav"))
    generate_ready_sound(str(assets_dir / "ready.wav"))
    generate_success_sound(str(assets_dir / "success.wav"))
    generate_error_sound(str(assets_dir / "error.wav"))
    
    print()
    print("Done! Audio assets generated successfully.")


if __name__ == "__main__":
    main()
