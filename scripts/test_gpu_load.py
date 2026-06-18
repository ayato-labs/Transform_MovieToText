import logging
import sys
import os

# Ensure the project root is in sys.path
sys.path.append(os.getcwd())

from src.core.whisper_transcriber import WhisperTranscriber

logging.basicConfig(level=logging.INFO)

def test_gpu_load():
    transcriber = WhisperTranscriber()
    print("\nAttempting to load 'tiny' model on GPU...")
    try:
        # Note: This will download the model if not present
        transcriber.load_model("tiny", force_gpu=True)
        print("SUCCESS: Model loaded on GPU.")
        
        # Test a tiny transcription
        import numpy as np
        audio = np.zeros(16000, dtype=np.float32)
        print("Testing tiny transcription...")
        res = transcriber.transcribe_numpy(audio, model_name="tiny")
        print(f"Transcription SUCCESS: {res['text']}")
        
    except Exception as e:
        print(f"FAILED to load/run on GPU: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gpu_load()
