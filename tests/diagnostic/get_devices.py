import re
import subprocess


def get_exact_audio_devices():
    result = subprocess.run(["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True)
    stderr = result.stderr.decode("utf-8", errors="ignore")

    # Example format: [dshow @ 0000014b1b0f4240]  "ステレオ ミキサー (Realtek(R) Audio)" (audio)
    matches = re.findall(r"\"(.*?)\"\s+\(audio\)", stderr)
    print("--- Exact Audio Device Names ---")
    for m in matches:
        print(f"DEVICE: [{m}]")


if __name__ == "__main__":
    get_exact_audio_devices()
