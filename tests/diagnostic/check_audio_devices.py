import subprocess
import re

def main():
    print("--- FFmpeg Audio Device Diagnostic ---")
    cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    _, stderr_bytes = proc.communicate(timeout=5)

    print("\n[Raw Device List from FFmpeg]")
    # Try common encodings
    for enc in ["cp932", "utf-8", "latin1"]:
        try:
            text = stderr_bytes.decode(enc, errors="ignore")
            # Filter only for audio devices
            lines = text.splitlines()
            audio_lines = []
            capture = False
            for line in lines:
                if "DirectShow audio devices" in line:
                    capture = True
                    continue
                if "DirectShow video devices" in line:
                    capture = False
                    continue
                if capture and "(audio)" in line:
                    audio_lines.append(line)
                    # Also get the next line for Alternative name
                    idx = lines.index(line)
                    if idx + 1 < len(lines) and "Alternative name" in lines[idx+1]:
                        audio_lines.append(lines[idx+1])
            
            if audio_lines:
                print(f"--- Decoded with {enc} ---")
                for al in audio_lines:
                    print(al)
                break
        except:
            continue

    print("\n[Advice]")
    print("If you want to record system audio (YouTube, etc.), look for 'Stereo Mix' or 'ステレオ ミキサー'.")
    print("If it's not listed above, follow these steps:")
    print("1. Right-click the Speaker icon in your taskbar -> 'Sound Settings'.")
    print("2. Go to 'More sound settings' (or 'Sound Control Panel').")
    print("3. Click the 'Recording' tab.")
    print("4. Right-click in the empty space -> 'Show Disabled Devices'.")
    print("5. Right-click 'Stereo Mix' and select 'Enable'.")

if __name__ == "__main__":
    main()
