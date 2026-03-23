import subprocess


def list_devices_brute():
    try:
        # Run and capture raw bytes
        result = subprocess.run(["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True)
        stderr = result.stderr

        encodings = ["utf-8", "cp932", "utf-16", "latin1"]
        for enc in encodings:
            try:
                print(f"--- Decoded with {enc} ---")
                print(stderr.decode(enc, errors="ignore"))
            except:
                pass

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_devices_brute()
