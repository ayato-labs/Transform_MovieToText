import argparse
import os
import shutil
import subprocess
import sys


def run_cmd(cmd):
    """Executes a shell command and prints its output."""
    print(f"Executing: {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if process.returncode != 0:
        print(f"Command failed with exit code {process.returncode}")
        sys.exit(process.returncode)


def cleanup_dist(dist_path):
    """Removes unnecessary files from the build directory."""
    print(f"Cleaning up {dist_path}...")
    
    # 1. Universal Cleanup (headers, libs, cmake, etc.)
    extensions_to_remove = [".h", ".lib", ".cmake", ".cpp", ".hpp", ".a"]
    folders_to_remove = ["__pycache__", "include", "cmake"]

    for root, dirs, files in os.walk(dist_path):
        # Remove folders
        for d in list(dirs):
            if d in folders_to_remove:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
                print(f"Removed folder: {d}")

        # Remove files by extension
        for f in files:
            if any(f.endswith(ext) for ext in extensions_to_remove):
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass


def pre_build_cleanup_venv():
    """Cleans the virtual environment before PyInstaller runs to reduce size."""
    venv_path = os.path.join(os.getcwd(), ".venv")
    if not os.path.exists(venv_path):
        return

    print(f"Pre-cleaning virtual environment at {venv_path} to reduce payload size...")
    extensions_to_remove = [".h", ".lib", ".cmake", ".cpp", ".hpp", ".a"]
    
    # We only clean Lib/site-packages to be safe
    # Note: We NO LONGER delete CUDA DLLs here because we want a unified GPU-ready build.
    sp_path = os.path.join(venv_path, "Lib", "site-packages")
    if not os.path.exists(sp_path):
        return

    for root, dirs, files in os.walk(sp_path):
        # Remove folders like __pycache__ or include
        for d in list(dirs):
            if d in ["__pycache__", "include", "cmake"]:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)

        for f in files:
            file_path = os.path.join(root, f)
            # Remove development files universally
            if any(f.endswith(ext) for ext in extensions_to_remove):
                try:
                    os.remove(file_path)
                except OSError:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Unified builder for TransformMovieToText EXE")
    parser.add_argument("--ci", action="store_true", help="Non-interactive mode for CI.")
    parser.add_argument("--onefile", action="store_true", help="Produce a single EXE file.")
    args = parser.parse_args()

    print("Building Unified Smart Executable...")

    # 1. Install Dependencies
    print("Installing base dependencies...")
    run_cmd("uv pip install -e .")
    run_cmd("uv pip install pyinstaller")

    # 2. Build Executable
    print("Starting PyInstaller build...")
    pre_build_cleanup_venv()
    
    exe_name = "TransformMovieToText"
    
    # Base PyInstaller command
    mode_flag = "--onefile" if args.onefile else "--onedir"
    
    pyinstaller_cmd = (
        f"uv run pyinstaller --noconfirm {mode_flag} --windowed "
        f'--name "{exe_name}" '
        '--icon "assets/icon.ico" '
        '--add-data "assets;assets" '
        "--collect-all whisper --collect-all tiktoken --collect-all flet "
        "--collect-all nvidia_cublas_cu12 --collect-all nvidia_cudnn_cu12 "
        "--collect-all nvidia_cuda_runtime_cu12 --collect-all nvidia_cuda_nvrtc_cu12 "
        "--exclude-module matplotlib --exclude-module notebook --exclude-module jedi "
        "--exclude-module IPython --exclude-module PIL.ImageQt "
        "main.py"
    )
    
    run_cmd(pyinstaller_cmd)

    # 3. Post-build Cleanup (Only for --onedir)
    if not args.onefile:
        dist_dir = os.path.join("dist", exe_name)
        if os.path.exists(dist_dir):
            cleanup_dist(dist_dir)

    print(f"\nBuild completed successfully!")
    if args.onefile:
        print(f"Executable file: dist/{exe_name}.exe")
    else:
        print(f"Executable directory: dist/{exe_name}")


if __name__ == "__main__":
    main()
