import re
import subprocess
import time
from pathlib import Path


def test_all_devices():
    print("--- Exhaustive Audio Device Capture Test ---")

    # 1. Get List of devices
    result = subprocess.run(
        ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    stderr = result.stderr
    matches = re.findall(r"\"(.*?)\"\s+\(audio\)", stderr)

    if not matches:
        print("No audio devices found via DirectShow!")
        return

    test_dir = Path("data/records/test_devices")
    test_dir.mkdir(parents=True, exist_ok=True)

    for i, device in enumerate(matches):
        print(f"\n[{i + 1}/{len(matches)}] Testing Device: {device}")
        out_file = test_dir / f"test_{i}.mp3"
        if out_file.exists():
            out_file.unlink()

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "dshow",
            "-i",
            f"audio={device}",
            "-t",
            "2",  # 2 seconds
            "-ac",
            "1",
            "-ar",
            "16000",
            str(out_file),
        ]

        start_time = time.time()
        print(f"Running: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        duration = time.time() - start_time

        if out_file.exists() and out_file.stat().st_size > 1000:
            print(f"✅ SUCCESS: Captured {out_file.stat().st_size} bytes from [{device}] in {duration:.2f}s")
        else:
            print(f"❌ FAILED to capture from [{device}]")
            print(f"Stderr tail: {proc.stderr[-200:]}")


if __name__ == "__main__":
    test_all_devices()
