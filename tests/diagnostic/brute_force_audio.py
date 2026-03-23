import os
import re
import subprocess

import numpy as np


def get_audio_devices():
    cmd = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    _, stderr = proc.communicate()

    devices = []
    # Try multiple decodings
    for enc in ["cp932", "utf-8", "latin1"]:
        try:
            text = stderr.decode(enc)
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "(audio)" in line:
                    match = re.search(r"\"(.*?)\"", line)
                    if match:
                        name = match.group(1)
                        # Check for GUID in next line
                        guid = ""
                        if i + 1 < len(lines) and "Alternative name" in lines[i + 1]:
                            g_match = re.search(r"\"(.*?)\"", lines[i + 1])
                            if g_match:
                                guid = g_match.group(1)
                        devices.append((name, guid))
            if devices:
                break
        except:
            continue
    return devices


def test_device(name_or_guid):
    print(f"Testing device: {name_or_guid}...")
    temp_file = "tests/temp_test.f32"
    if os.path.exists(temp_file):
        os.remove(temp_file)

    cmd = ["ffmpeg", "-y", "-t", "3", "-f", "dshow", "-i", f"audio={name_or_guid}", "-ac", "1", "-ar", "16000", "-f", "f32le", temp_file]

    try:
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.communicate(timeout=10)

        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
            data = np.fromfile(temp_file, dtype=np.float32)
            peak = np.abs(data).max()
            rms = np.sqrt(np.mean(data**2))
            print(f"  SUCCESS! Peak: {peak:.6f}, RMS: {rms:.6f}, Samples: {len(data)}")
            return peak, rms
        else:
            print("  FAILED: No data captured.")
            return 0, 0
    except Exception as e:
        print(f"  ERROR: {e}")
        return 0, 0
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    devices = get_audio_devices()
    print(f"Found {len(devices)} audio devices.")

    results = []
    for name, guid in devices:
        # Prefer GUID if available
        target = guid if guid else name
        peak, rms = test_device(target)
        results.append({"name": name, "target": target, "peak": peak, "rms": rms})

    print("\n" + "=" * 50)
    print("DEVICE SUMMARY (Sorted by Peak Volume)")
    results.sort(key=lambda x: x["peak"], reverse=True)
    for r in results:
        print(f"Peak: {r['peak']:.6f} | Name: {r['name']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
