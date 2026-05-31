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


def cleanup_dist(dist_path, build_type):
    """Removes unnecessary files from the build directory."""
    print(f"Cleaning up {dist_path}...")
    
    # 1. Universal Cleanup (headers, libs, cmake, etc.)
    extensions_to_remove = [".h", ".lib", ".cmake", ".cpp", ".hpp", ".a"]
    folders_to_remove = ["__pycache__", "include", "cmake"]

    for root, dirs, files in os.walk(dist_path):
        # Remove folders
        for d in dirs:
            if d in folders_to_remove:
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                print(f"Removed folder: {d}")

        # Remove files by extension
        for f in files:
            if any(f.endswith(ext) for ext in extensions_to_remove):
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass

    # 2. CPU-specific Cleanup (Surgery for CUDA remnants)
    if build_type == "cpu":
        # PyTorch often includes CUDA DLLs even in CPU builds if not carefully handled.
        cuda_keywords = ["cuda", "cublas", "cudnn", "nvrtc", "nvjitlink", "cufft", "curand", "cusparse", "cusolver"]
        # Search everywhere in the dist folder for these, though they usually live in torch/lib
        for root, dirs, files in os.walk(dist_path):
            for f in files:
                if any(kw in f.lower() for kw in cuda_keywords) and f.endswith(".dll"):
                    try:
                        os.remove(os.path.join(root, f))
                        print(f"Removed CUDA remnant from CPU build: {f}")
                    except OSError:
                        pass


def check_gpu():
    """Checks for NVIDIA GPU availability via nvidia-smi."""
    try:
        subprocess.run(["nvidia-smi"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Smart builder for TransformMovieToText EXE")
    parser.add_argument(
        "--type",
        choices=["gpu", "cpu", "auto"],
        default="auto",
        help="Force build type (gpu, cpu) or use 'auto' for detection.",
    )
    parser.add_argument("--ci", action="store_true", help="Non-interactive mode for CI.")
    args = parser.parse_args()

    # 1. Determine Build Type
    build_type = args.type
    if build_type == "auto":
        print("Detecting GPU...")
        if check_gpu():
            print("NVIDIA GPU detected.")
            if args.ci:
                build_type = "gpu"
            else:
                ans = input("GPU version of Torch? (Y/n): ").strip().lower()
                build_type = "gpu" if ans != "n" else "cpu"
        else:
            print("No NVIDIA GPU detected.")
            build_type = "cpu"

    print(f"Building for: {build_type.upper()}")

    # 2. Install Dependencies
    print("Installing base dependencies...")
    run_cmd("uv pip install -e .")
    run_cmd("uv pip install pyinstaller")

    if build_type == "gpu":
        print("Installing GPU-enabled PyTorch (CUDA 12.1)...")
        run_cmd(
            "uv pip install torch==2.5.1+cu121 "
            "torchaudio==2.5.1+cu121 --extra-index-url "
            "https://download.pytorch.org/whl/cu121"
        )
    else:
        print("Installing CPU-only PyTorch...")
        run_cmd(
            "uv pip install torch==2.5.1+cpu "
            "torchaudio==2.5.1+cpu --extra-index-url "
            "https://download.pytorch.org/whl/cpu"
        )

    # 3. Build Executable
    print("Starting PyInstaller build...")
    # Use unique name based on build type
    exe_name = f"TransformMovieToText_{build_type.upper()}"
    
    # Base PyInstaller command
    pyinstaller_cmd = (
        "uv run pyinstaller --noconfirm --onedir --windowed "
        f'--name "{exe_name}" '
        '--icon "assets/icon.ico" '
        '--add-data "assets;assets" '
        "--collect-all whisper --collect-all tiktoken --collect-all flet "
        "--exclude-module matplotlib --exclude-module notebook --exclude-module jedi "
        "--exclude-module IPython --exclude-module PIL.ImageQt "
        "--exclude-module torch.testing --exclude-module torch.distributed "
        "main.py"
    )
    
    # Optimization: Only collect necessary torch data
    # For CPU, we exclude CUDA entirely
    if build_type == "cpu":
        pyinstaller_cmd += " --exclude-module torch.cuda --exclude-module triton"
    
    run_cmd(pyinstaller_cmd)

    # 4. Post-build Cleanup
    dist_dir = os.path.join("dist", exe_name)
    if os.path.exists(dist_dir):
        cleanup_dist(dist_dir, build_type)

    print(f"\nBuild completed successfully!")
    print(f"Executable directory: {dist_dir}")


if __name__ == "__main__":
    main()
