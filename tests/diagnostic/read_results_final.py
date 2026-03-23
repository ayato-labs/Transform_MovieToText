import os

log_path = "tests/diagnostic_final_verification.log"
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    text = data.decode("utf-16le", errors="ignore")
    relevant_lines = []
    for line in text.splitlines():
        if any(kw in line for kw in ["RMS", "Peak", "TRANSCRIPTION RESULT", "VAD OFF", "VAD ON", "VAD filter removed", "VAD filter:"]):
            relevant_lines.append(line.strip())

    for l in relevant_lines:
        print(l)

    import re

    results = re.findall(r"\[(.*?)\]", text)
    if results:
        print("\nBracketed Results Found:")
        for r in results:
            if len(r.strip()) > 0:
                print(f" - {r}")
else:
    print("Log file not found.")
