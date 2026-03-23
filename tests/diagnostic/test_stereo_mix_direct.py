import os
import re
import subprocess


def test_stereo_mix_variants():
    # 1. Get full list with GUIDs
    result = subprocess.run(
        ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    stderr = result.stderr
    print("--- FFmpeg DirectShow List ---")
    print(stderr)

    # Search for Stereo Mix and its alternative name
    # Example: [dshow @ ...]  "ステレオ ミキサー (Realtek(R) Audio)" (audio)
    #          [dshow @ ...]    Alternative name "@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\wave_{C39EBE5D-4E15-4D1D-A1A6-027986C20A2E}"

    variants = []

    # 1. Logic to extract names and GUIDs specifically for Stereo Mix
    lines = stderr.splitlines()
    for i, line in enumerate(lines):
        if any(kw in line for kw in ["ステレオ ミキサー", "Stereo Mix"]):
            # Found the primary name line
            m_name = re.search(r"\"(.*?)\"", line)
            if m_name:
                variants.append(m_name.group(1))

            # Look at the next few lines for 'Alternative name'
            for j in range(i + 1, min(i + 5, len(lines))):
                if "Alternative name" in lines[j]:
                    m_guid = re.search(r"Alternative name \"(.*?)\"", lines[j])
                    if m_guid:
                        variants.append(m_guid.group(1))
                    break

    if not variants:
        print("No Stereo Mix variants found in FFmpeg output!")
        # Add a default fallback just in case
        variants = ["ステレオ ミキサー (Realtek(R) Audio)"]

    print(f"Testing these target variants: {variants}")

    for variant in variants:
        print(f"\n>> Testing variant: {variant}")
        out_file = f"tests/test_record_{variants.index(variant)}.mp3"
        if os.path.exists(out_file):
            os.remove(out_file)

        cmd = ["ffmpeg", "-y", "-f", "dshow", "-i", f"audio={variant}", "-t", "2", "-ac", "1", "-ar", "16000", out_file]
        print(f"Running: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")

        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
            print(f"✅ SUCCESS for [{variant}]")
        else:
            print(f"❌ FAILED for [{variant}]")
            print(f"Error tail: {proc.stderr[-300:]}")


if __name__ == "__main__":
    test_stereo_mix_variants()
