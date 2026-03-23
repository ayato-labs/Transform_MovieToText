import os

log_path = "tests/ruff_report.txt"
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    # Try multiple decodings for Windows UTF-16
    for enc in ["utf-16le", "cp932", "utf-8"]:
        try:
            text = data.decode(enc)
            print(f"--- Decoded with {enc} ---")
            print(text)
            break
        except:
            continue
else:
    print("Report file not found.")
