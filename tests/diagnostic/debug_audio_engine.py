import logging
import sys
import io
import soundcard as sc
import numpy as np
import time
import wave

# Force UTF-8 for Windows output redirection
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Monkey-patch soundcard compatibility with newer numpy
if not hasattr(np, 'fromstring') or np.fromstring.__name__ != 'frombuffer':
    import numpy
    numpy.fromstring = numpy.frombuffer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioDebug")

def main():
    print("=== SoundCard Audio Engine Debugging ===")
    
    # 1. Device Enumeration
    mics = sc.all_microphones(include_loopback=True)
    print(f"\n[Detected Microphones/Loopbacks]")
    target_mic = None
    for i, m in enumerate(mics):
        is_loop = "loopback" in m.name.lower() or "speaker" in m.name.lower() or "スピーカー" in m.name
        print(f"  [{i}] {m.name} {'(Candidate)' if is_loop else ''}")
        if is_loop and not target_mic:
            target_mic = m

    if not target_mic:
        print("\nERROR: No loopback device found. Please play some audio and check Windows settings.")
        return

    print(f"\n[Targeting Device]: {target_mic.name}")
    
    # 2. Capture Simulation (Exact copy of recorder logic)
    sample_rate = 16000
    duration_sec = 10
    total_samples = sample_rate * duration_sec
    captured_data = []
    
    print(f"\nRecording {duration_sec} seconds... PLEASE PLAY AUDIO NOW!")
    
    try:
        with target_mic.recorder(samplerate=sample_rate) as recorder:
            start_time = time.time()
            while len(captured_data) * 1600 < total_samples:
                # Read 0.1s chunks (same as app)
                chunk = recorder.record(numframes=1600)
                
                # Mono conversion (same as app)
                if chunk.ndim > 1 and chunk.shape[1] > 1:
                    chunk = np.mean(chunk, axis=1)
                elif chunk.ndim > 1:
                    chunk = chunk.flatten()
                
                captured_data.append(chunk.astype(np.float32))
        
        full_audio = np.concatenate(captured_data)
        
        # 3. Stats Analysis
        peak = np.abs(full_audio).max()
        rms = np.sqrt(np.mean(full_audio**2))
        print(f"\n[Capture Results Summary]")
        print(f"  Samples: {len(full_audio)}")
        print(f"  Peak Volume: {peak:.6f}")
        print(f"  RMS Volume: {rms:.6f}")
        
        if peak < 0.0001:
            print("\nRESULT: SILENCE DETECTED. The loopback device is not receiving signal.")
        elif peak < 0.01:
            print("\nRESULT: VERY LOW VOLUME. Whisper might hallucinate.")
        else:
            print("\nRESULT: AUDIO DETECTED! Signal looks healthy.")

        # 4. Save to WAV for user verification
        output_file = "tests/debug_capture.wav"
        with wave.open(output_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(4) # float32
            wf.setframerate(sample_rate)
            wf.writeframes(full_audio.tobytes())
        print(f"\nSaved capture to: {output_file}")
        print("Please listen to this file to check if the sound is clear.")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
