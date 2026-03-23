"""
Test script using pyaudiowpatch for WASAPI loopback capture.
This replaces the broken soundcard-based approach.
Based on the official example:
https://github.com/s0d3s/PyAudioWPatch/blob/master/examples/pawp_record_wasapi_loopback.py
"""
import pyaudiowpatch as pyaudio
import numpy as np
import time
import wave
import struct

DURATION = 5.0
CHUNK_SIZE = 512

def main():
    print("=== PyAudioWPatch WASAPI Loopback Test ===")
    
    with pyaudio.PyAudio() as p:
        # 1. Find WASAPI Host API
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("[ERROR] WASAPI is not available on this system.")
            return
        
        # 2. Find default loopback device
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        print(f"Default Speaker: {default_speakers['name']}")
        print(f"  Sample Rate: {int(default_speakers['defaultSampleRate'])}Hz")
        print(f"  Channels: {default_speakers['maxInputChannels']}")
        
        if not default_speakers["isLoopbackDevice"]:
            for loopback in p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                print("[ERROR] Default loopback device not found.")
                return
        
        print(f"Loopback Device: {default_speakers['name']}")
        
        # 3. Record for DURATION seconds
        sample_rate = int(default_speakers["defaultSampleRate"])
        channels = default_speakers["maxInputChannels"]
        
        wav_path = "tests/pyaudio_loopback.wav"
        wave_file = wave.open(wav_path, 'wb')
        wave_file.setnchannels(channels)
        wave_file.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
        wave_file.setframerate(sample_rate)
        
        all_frames = []
        
        def callback(in_data, frame_count, time_info, status):
            wave_file.writeframes(in_data)
            all_frames.append(in_data)
            return (in_data, pyaudio.paContinue)
        
        print(f"\nRecording {DURATION}s at {sample_rate}Hz, {channels}ch...")
        print("[!] PLAY AUDIO NOW (YouTube etc.)")
        
        with p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            frames_per_buffer=CHUNK_SIZE,
            input=True,
            input_device_index=default_speakers["index"],
            stream_callback=callback
        ) as stream:
            time.sleep(DURATION)
        
        wave_file.close()
        print(f"Saved WAV: {wav_path}")
        
        # 4. Analyze captured audio
        raw_bytes = b''.join(all_frames)
        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        
        # Convert to mono float32 for Whisper
        if channels > 1:
            audio_int16 = audio_int16.reshape(-1, channels)
            audio_mono = audio_int16.mean(axis=1)
        else:
            audio_mono = audio_int16.astype(np.float32)
        
        audio_float = audio_mono / 32768.0
        audio_float = audio_float.astype(np.float32)
        
        peak = np.abs(audio_float).max()
        rms = np.sqrt(np.mean(audio_float**2))
        print(f"\nAudio Stats:")
        print(f"  Peak: {peak:.5f}")
        print(f"  RMS:  {rms:.5f}")
        print(f"  Samples: {len(audio_float)}")
        
        if peak < 0.001:
            print("WARNING: Audio is silent!")
            return
        
        # 5. Whisper Direct Test
        print("\nLoading Whisper model...")
        from faster_whisper import WhisperModel
        model = WhisperModel("medium", device="cuda", compute_type="float16")
        
        # Resample to 16kHz for Whisper if needed
        if sample_rate != 16000:
            import torch
            import torchaudio
            tensor = torch.from_numpy(audio_float).unsqueeze(0)
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            audio_16k = resampler(tensor).squeeze(0).numpy()
            print(f"  Resampled: {sample_rate}Hz -> 16000Hz ({len(audio_16k)} samples)")
        else:
            audio_16k = audio_float
        
        print("Transcribing...")
        segments, info = model.transcribe(
            audio_16k,
            beam_size=5,
            language="ja",
            vad_filter=False,
            condition_on_previous_text=False,
        )
        
        text = "".join([s.text for s in list(segments)]).strip()
        print(f"\n[TRANSCRIPTION RESULT]\n{text}")
        print(f"\n=== DONE === ")
        print(f"Please also listen to {wav_path} to verify it sounds correct!")

if __name__ == "__main__":
    main()
