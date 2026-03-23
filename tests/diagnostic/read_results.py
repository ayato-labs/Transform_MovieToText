import os

log_path = "tests/diagnostic_full.log"
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    text = data.decode("utf-16le", errors="ignore")
    for line in text.splitlines():
        if any(kw in line for kw in ["RMS", "Peak", "TRANSCRIPTION RESULT", "VAD OFF", "VAD ON", "VAD filter removed"]):
            print(line.strip())
        # Also print the next line after TRANSCRIPTION RESULT if it looks like the result
        if "TRANSCRIPTION RESULT" in line or "VAD ON" in line or "VAD OFF" in line:
            pass  # we look for the next few lines

    # Simple search for bracketed results
    import re

    results = re.findall(r"\[(.*?)\]", text)
    if results:
        print("\nBracketed Results Found:")
        for r in results:
            print(f" - {r}")
else:
    print("Log file not found.")
