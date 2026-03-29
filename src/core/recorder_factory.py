# Compatibility shim for src.recorder
from src.recorder.audio_recorder import AudioRecorder
from src.recorder.base import _BaseRecorder
from src.recorder.factory import create_recorder
from src.recorder.ffmpeg import FFmpegRecorder

__all__ = ["_BaseRecorder", "FFmpegRecorder", "AudioRecorder", "create_recorder"]
