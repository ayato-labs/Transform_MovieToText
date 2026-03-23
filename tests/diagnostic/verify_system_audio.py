import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.logger import setup_logger
from src.recorder.factory import create_recorder

setup_logger()
logger = logging.getLogger(__name__)


def test_system_audio_capture():
    logger.info("Starting System Audio Capture Verification...")

    mp3_path = Path("data/records/test/system_audio_verify.mp3")
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    if mp3_path.exists():
        mp3_path.unlink()

    recorder = create_recorder(source="system", mp3_path=str(mp3_path))

    try:
        logger.info("Starting recorder...")
        recorder.start()

        # In FFmpegRecorder, target_name should be logged
        logger.info("Recording system audio for 5 seconds (PLAY SOME AUDIO NOW!)...")
        time.sleep(5)

        logger.info("Stopping recorder...")
        recorder.stop()

        if mp3_path.exists():
            size = mp3_path.stat().st_size
            if size > 1024:
                logger.info(f"✅ Success! Generated MP3 file: {mp3_path} ({size} bytes)")
            else:
                logger.warning(f"⚠️ File generated but too small: {size} bytes. Audio might not be playing.")
        else:
            logger.error("❌ Failed: MP3 file was not generated.")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_system_audio_capture()
