import logging
import os
import re
import subprocess
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.recorder.ffmpeg import FFmpegRecorder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_discovery():
    print("--- Debugging FFmpegRecorder Discovery ---")
    FFmpegRecorder()

    # Manually trigger the discovery helper and print intermediate steps
    cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    _, stderr_bytes = proc.communicate(timeout=5)

    found = False
    for encoding in ["utf-8", "cp932", "latin1"]:
        print(f"\n[Enc: {encoding}] Decoding...")
        try:
            stderr = stderr_bytes.decode(encoding, errors="ignore")
            lines = stderr.splitlines()
            keywords = ["ステレオ ミキサー", "Stereo Mix", "Rec. Playback", "Virtual Audio", "Wave Out"]

            for i, line in enumerate(lines):
                if any(kw in line for kw in keywords) and "(audio)" in line:
                    print(f"  MATCH FOUND: {line}")
                    if i + 1 < len(lines) and "Alternative name" in lines[i + 1]:
                        print(f"  ALT NAME LINE: {lines[i + 1]}")
                        guid_match = re.search(r"Alternative name \"(.*?)\"", lines[i + 1])
                        if guid_match:
                            print(f"  GUID CAPTURED: {guid_match.group(1)}")
                            found = True
                    else:
                        print("  No alternative name found on next line.")
                        name_match = re.search(r"\"(.*?)\"", line)
                        if name_match:
                            print(f"  NAME CAPTURED: {name_match.group(1)}")
                            found = True
        except Exception as e:
            print(f"  Error decoding: {e}")

    if not found:
        print("\n!!! NO SYSTEM AUDIO DEVICE DISCOVERED !!!")


if __name__ == "__main__":
    debug_discovery()
