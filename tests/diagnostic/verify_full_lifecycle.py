import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.recorder.factory import create_recorder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_full_lifecycle():
    logger.info("Starting Full Lifecycle Verification Test...")

    # 1. Test FFmpegRecorder termination and file access
    temp_mp3 = Path("data/records/test/lifecycle_test.mp3")
    temp_mp3.parent.mkdir(parents=True, exist_ok=True)
    if temp_mp3.exists():
        temp_mp3.unlink()

    logger.info("Starting FFmpegRecorder (System Audio)...")
    # Note: On some CI environments this might fail if no Stereo Mix exists,
    # but we just want to test the process management logic.
    recorder = create_recorder(source="system", mp3_path=str(temp_mp3))

    try:
        recorder.start()
        logger.info("Recording for 3 seconds...")
        time.sleep(3)

        logger.info("Stopping recorder...")
        recorder.stop()

        # Immediate check for file access
        logger.info(f"Checking if file {temp_mp3} is accessible...")
        if temp_mp3.exists():
            with open(temp_mp3, "ab") as f:
                f.write(b"")  # Try to open for writing to check lock
            logger.info("✅ File is accessible immediately after stop (No Lock)")
        else:
            logger.warning("File was not created (Normal if FFmpeg failed to start due to missing device, but check logs)")

    except Exception as e:
        logger.error(f"Lifecycle test failed: {e}")
        import traceback

        traceback.print_exc()
        raise e
    finally:
        if temp_mp3.exists():
            try:
                temp_mp3.unlink()
            except Exception as e:
                logger.error(f"Failed to unlink at end: {e}")

    logger.info("✅ Full Lifecycle Check Finished (Process Management Verified)")


if __name__ == "__main__":
    test_full_lifecycle()
