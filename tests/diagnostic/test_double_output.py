import os
import subprocess
import time


def test_double_output():
    print("Testing FFmpeg Dual Output (PCM + MP3)...")
    pcm_file = "tests/test_output.pcm"
    mp3_file = "tests/test_output.mp3"

    for f in [pcm_file, mp3_file]:
        if os.path.exists(f):
            os.remove(f)

    # Use the verified GUID or "Stereo Mix"
    device = "audio=@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\\wave_{87BD51FA-F339-4C0D-A98E-7EDA495DDBD1}"

    # The command used in the app:
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "dshow",
        "-i",
        device,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "f32le",
        "-",  # Output 1: stdout
        "-f",
        "mp3",
        "-ac",
        "1",
        "-ab",
        "64k",
        mp3_file,  # Output 2: file
    ]

    print(f"Running: {' '.join(command)}")

    try:
        # We'll read from stdout and write to pcm_file manually to verify PCM stream
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        pcm_data = []
        start_time = time.time()
        while time.time() - start_time < 5:
            chunk = proc.stdout.read(4096)
            if chunk:
                pcm_data.append(chunk)
            else:
                break

        proc.terminate()
        proc.wait(timeout=2)

        print(f"Captured {len(pcm_data)} PCM chunks from stdout.")
        if os.path.exists(mp3_file) and os.path.getsize(mp3_file) > 1000:
            print(f"SUCCESS: MP3 file generated ({os.path.getsize(mp3_file)} bytes).")
        else:
            print("FAILED: MP3 file is missing or too small.")
            # Check stderr
            stderr = proc.stderr.read().decode("utf-8", errors="ignore")
            print(f"FFmpeg Stderr:\n{stderr}")

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    test_double_output()
