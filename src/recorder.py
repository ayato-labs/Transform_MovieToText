# Compatibility shim for src.recorder
from .recorder.audio_recorder import AudioRecorder
from .recorder.base import _BaseRecorder
from .recorder.factory import create_recorder
from .recorder.ffmpeg import FFmpegRecorder

__all__ = ["_BaseRecorder", "FFmpegRecorder", "AudioRecorder", "create_recorder"]
