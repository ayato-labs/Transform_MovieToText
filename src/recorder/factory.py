from .audio_recorder import AudioRecorder
from .soundcard_recorder import SoundCardRecorder


def create_recorder(output_dir="temp_chunks", segment_time=30, overlap=5, source="system", mp3_path=None):
    """Factory to return the appropriate recorder based on source."""
    if source == "system":
        return SoundCardRecorder(output_dir, segment_time, overlap, source, mp3_path=mp3_path)
    else:
        return AudioRecorder(output_dir, segment_time, overlap, source, mp3_path=mp3_path)
