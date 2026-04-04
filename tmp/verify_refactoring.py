import sys
import os

# Add src to path
sys.path.append(os.getcwd())

def test_imports():
    print("Testing major component imports after decoupling...")
    try:
        from src.app import main as app_main
        print("✓ src.app.main imported")
        
        from src.platforms.desktop.app import DesktopApp
        print("✓ src.platforms.desktop.app.DesktopApp imported")
        
        from src.platforms.android.app import AndroidApp
        print("✓ src.platforms.android.app.AndroidApp imported")
        
        from src.core.transcription_service import TranscriptionService
        print("✓ src.core.transcription_service.TranscriptionService imported")
        
        from src.core.live_processor import LiveTranscriptionManager
        print("✓ src.core.live_processor.LiveTranscriptionManager imported")
        
        from src.platforms.desktop.ui.main_window import MainWindow
        print("✓ src.platforms.desktop.ui.main_window.MainWindow imported")
        
        print("\nAll major imports are working correctly!")
        return True
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_imports():
        sys.exit(0)
    else:
        sys.exit(1)
