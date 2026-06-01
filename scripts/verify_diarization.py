"""
PoC: Speaker Diarization using sherpa-onnx and CAM++ (PyTorch-free).
This script demonstrates the feasibility of ADR-0002.
"""

import sys
import os
import wave
import numpy as np

try:
    import sherpa_onnx
except ImportError:
    print("Error: sherpa-onnx not installed. Run 'pip install sherpa-onnx'")
    sys.exit(1)

def verify_diarization(wav_path, segmentation_model, embedding_model):
    """
    Runs speaker diarization on a WAV file.
    Note: Requires 16kHz mono WAV.
    """
    print(f"Loading models...")
    print(f" - Segmentation: {segmentation_model}")
    print(f" - Embedding: {embedding_model}")

    # Config setup
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=segmentation_model,
            ),
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingModelConfig(
            model=embedding_model,
        ),
        clustering=sherpa_onnx.FastClusteringConfig(
            # num_clusters=2, # Optional: if known
            threshold=0.5,
        ),
    )

    if not config.validate():
        print("Error: Invalid configuration or missing model files.")
        return

    sd = sherpa_onnx.OfflineSpeakerDiarization(config)

    # Load audio
    with wave.open(wav_path, "rb") as f:
        if f.getnchannels() != 1 or f.getframerate() != 16000:
            print("Error: Audio must be 16kHz mono WAV.")
            return
        
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768

    print(f"Processing diarization for {wav_path}...")
    segments = sd.process(samples)

    print("\n--- Diarization Results ---")
    for s in segments:
        print(f"[{s.start:6.2f}s -> {s.end:6.2f}s] Speaker {s.speaker}")

if __name__ == "__main__":
    # This is a plan/template. In a real environment, 
    # the user would need to provide the paths to the ONNX models.
    # Models can be downloaded from:
    # https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models
    
    print("Verification Script Initialized.")
    print("To run this PoC, you need to download the following models:")
    print("1. pyannote-segmentation-3.0.onnx")
    print("2. cam++_voxceleb_common.onnx")
    
    # Placeholder for actual testing logic
    if len(sys.argv) < 4:
        print("\nUsage: python verify_diarization.py <wav_path> <seg_model_path> <emb_model_path>")
    else:
        verify_diarization(sys.argv[1], sys.argv[2], sys.argv[3])
