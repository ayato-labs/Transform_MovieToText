import os

log_path = "tests/diagnostic_full.log"
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    # Try common Windows encodings
    for enc in ["utf-16le", "cp932", "utf-8"]:
        try:
            print(f"--- Encoding: {enc} ---")
            print(data.decode(enc, errors="ignore"))
            break
        except Exception:
            continue
else:
    print("Log file not found.")
