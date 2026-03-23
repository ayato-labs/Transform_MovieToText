import subprocess


def list_devices():
    try:
        # Use subprocess.run to capture output in one go
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
            encoding="utf-8",  # Try utf-8 first
            errors="ignore",
        )
        # FFmpeg outputs list_devices to stderr
        print("--- FFmpeg Stderr (Devices) ---")
        print(result.stderr)

        # Also try 'cp932' for Japanese Windows if utf-8 fails to show Japanese correctly
        result_jp = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True, text=True, encoding="cp932", errors="ignore"
        )
        print("--- FFmpeg Stderr (Devices CP932) ---")
        print(result_jp.stderr)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_devices()
