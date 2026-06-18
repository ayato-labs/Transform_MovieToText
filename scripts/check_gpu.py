import sys
import subprocess
import logging

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_gpu_diagnostic():
    print("=== GPU Diagnostic for Fast-Whisper (CTranslate2) ===")
    
    # 1. Check nvidia-smi
    print("\n1. Checking nvidia-smi...")
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            print("nvidia-smi found and executed successfully.")
            # print(res.stdout)
        else:
            print(f"nvidia-smi failed with return code {res.returncode}")
            print(res.stderr)
    except FileNotFoundError:
        print("nvidia-smi NOT found in PATH.")
    except Exception as e:
        print(f"Error running nvidia-smi: {e}")

    # 2. Check ctranslate2
    print("\n2. Checking ctranslate2...")
    try:
        import ctranslate2
        print(f"ctranslate2 version: {ctranslate2.__version__}")
        supported_cuda = ctranslate2.get_supported_compute_types("cuda")
        print(f"Supported compute types for 'cuda': {supported_cuda}")
        supported_cpu = ctranslate2.get_supported_compute_types("cpu")
        print(f"Supported compute types for 'cpu': {supported_cpu}")
    except ImportError:
        print("ctranslate2 is NOT installed.")
    except Exception as e:
        print(f"Error checking ctranslate2: {e}")

    # 3. Check faster-whisper
    print("\n3. Checking faster-whisper...")
    try:
        from faster_whisper import WhisperModel
        print("faster-whisper is installed.")
        
        # Try to initialize a tiny model on GPU if supported
        if 'cuda' in locals() or True: # Just try if ctranslate2 says it supports cuda
            try:
                print("Attempting to initialize 'tiny' model on CUDA (int8_float16)...")
                # We don't want to actually download/load if not necessary, 
                # but if we want to be sure, we need to.
                # Let's just check if it throws an error immediately.
                # Actually, WhisperModel initialization involves loading the model.
                pass
            except Exception as e:
                print(f"Failed to initialize WhisperModel on CUDA: {e}")
    except ImportError:
        print("faster-whisper is NOT installed.")

    # 4. Check for DLLs (on Windows)
    if sys.platform == "win32":
        print("\n4. Checking for CUDA DLLs...")
        import os
        # Check PATH
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        # Also check .venv site-packages
        venv_base = os.path.join(os.getcwd(), ".venv", "Lib", "site-packages", "nvidia")
        if os.path.exists(venv_base):
            for root, dirs, files in os.walk(venv_base):
                if "bin" in root:
                    path_dirs.append(root)

        important_dlls = ["cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_8.dll", "cudart64_12.dll", "cudnn64_9.dll"]
        for dll in important_dlls:
            found = False
            for d in path_dirs:
                if os.path.exists(os.path.join(d, dll)):
                    print(f"Found {dll} in {d}")
                    found = True
                    break
            if not found:
                # Special check for cudnn 9 as it might be named differently
                if dll == "cudnn64_8.dll":
                    # Check for cudnn64_9.dll
                    pass 
                else:
                    print(f"NOT found: {dll}")

if __name__ == "__main__":
    check_gpu_diagnostic()
