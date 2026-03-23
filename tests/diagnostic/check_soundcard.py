import soundcard as sc


def check_soundcard_loopback():
    print("--- Soundcard Speakers (Loopback Check) ---")
    try:
        speakers = sc.all_speakers()
        for i, s in enumerate(speakers):
            print(f"[{i}] {s.name}")
            # Check if we can get a recorder from this speaker
            try:
                # Some soundcard versions support s.recorder(loopback=True)
                # Let's check available methods
                methods = dir(s)
                print(f"    Methods: {'player' in methods}, {'recorder' in methods}")
                if "recorder" in methods:
                    print("    YES! This speaker has a recorder (Loopback compatible)")
            except Exception as e:
                print(f"    Error checking recorder: {e}")

        print("\n--- Soundcard Microphones ---")
        mics = sc.all_microphones()
        for i, m in enumerate(mics):
            print(f"[{i}] {m.name}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_soundcard_loopback()
