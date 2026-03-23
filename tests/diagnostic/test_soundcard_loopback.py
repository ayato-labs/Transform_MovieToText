import soundcard as sc
import numpy as np
import time

def main():
    print("--- SoundCard Loopback Diagnostic ---")
    try:
        # Get all speakers (for loopback, speakers are treated as microphones)
        speakers = sc.all_speakers()
        print(f"Found {len(speakers)} speakers:")
        for i, s in enumerate(speakers):
            print(f"  [{i}] {s.name}")

        # Try to get the default speaker's loopback microphone
        default_speaker = sc.default_speaker()
        print(f"\nDefault Speaker: {default_speaker.name}")
        
        # In soundcard, we use get_microphone with include_loopback=True 
        # or we find a microphone that has the same name as the speaker but is a loopback.
        mics = sc.all_microphones(include_loopback=True)
        print(f"\nFound {len(mics)} microphones (including loopback):")
        target_mic = None
        for i, m in enumerate(mics):
            is_loopback = "loopback" in m.name.lower() or "スピーカー" in m.name or "Speaker" in m.name
            print(f"  [{i}] {m.name} {'(Loopback candidate!)' if is_loopback else ''}")
            if is_loopback and not target_mic:
                target_mic = m

        if not target_mic:
            print("ERROR: No loopback microphone found.")
            return

        print(f"\nAttempting to record 3 seconds from: {target_mic.name}")
        with target_mic.recorder(samplerate=16000) as recorder:
            data = recorder.record(numframes=16000*3)
            peak = np.abs(data).max()
            print(f"Recording successful! Peak volume: {peak:.6f}")
            if peak > 1e-6:
                print("SUCCESS: Audio detected!")
            else:
                print("WARNING: Captured only silence. Is audio playing?")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
