import os
import sys
import time

import numpy as np

# Add current directory to path so it can find src
sys.path.append(os.getcwd())

from src.recorder.ffmpeg import FFmpegRecorder
from src.transcriber import WhisperTranscriber


def main():
    print("Definitive System Audio Loopback Test")

    # 1. Setup
    output_wav = "tests/verification_output.wav"
    if os.path.exists(output_wav):
        os.remove(output_wav)

    recorder = FFmpegRecorder(segment_time=10, source="system")
    transcriber = WhisperTranscriber()

    # 2. Start Recording
    print("Recording 10 seconds of system audio (Please play some sound)...")
    recorder.start()
    time.sleep(12)
    recorder.stop()

    # 3. Process Chunk
    if recorder.chunk_queue.empty():
        print("ERROR: No audio chunks captured in queue.")
        return

    audio_data = recorder.chunk_queue.get()
    peak = np.abs(audio_data).max()
    rms = np.sqrt(np.mean(audio_data**2))
    print(f"Volume - Peak: {peak:.6f}, RMS: {rms:.6f}")

    # 4. Save to WAV for user verification
    import wave

    with wave.open(output_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4)  # 32-bit float
        wf.setframerate(16000)
        wf.writeframes((audio_data).tobytes())
    print(f"Saved raw audio to {output_wav}")

    # 5. Transcribe
    print("Transcribing...")
    text = transcriber.transcribe(audio_data, model_name="turbo", language="ja")
    print(f"Result: [{text}]")


if __name__ == "__main__":
    main()
