import subprocess


def test_wasapi_loopback():
    print("--- WASAPI Loopback Brute Force Test ---")

    # Try common WASAPI loopback device patterns
    # In WASAPI, it's often the output device name
    # We can try to list them better

    # Try to find output devices first
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "wasapi", "-list_devices", "true", "-i", "dummy"],
        capture_output=True,
        text=True,
        encoding="utf-8",  # Might need cp932 for Japanese
        errors="ignore",
    )
    stderr = result.stderr
    print("--- FFmpeg WASAPI stderr ---")
    print(stderr)

    # Another way to list wasapi devices
    print("\n--- Trying WASAPI -list_devices again (encoding cp932) ---")
    result_jp = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "wasapi", "-list_devices", "true", "-i", "dummy"],
        capture_output=True,
        text=True,
        encoding="cp932",
        errors="ignore",
    )
    print(result_jp.stderr)


if __name__ == "__main__":
    test_wasapi_loopback()
