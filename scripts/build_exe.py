import argparse
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
            "uv pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 "
            "torchaudio==2.5.1+cu121 --extra-index-url "
            "https://download.pytorch.org/whl/cu121"
        )
    else:
        print("Installing CPU version of PyTorch...")
        run_cmd("uv pip install torch torchvision torchaudio")

    # 3. Build Executable
    print("Starting PyInstaller build...")
    # Use unique name based on build type
    exe_name = f"TransformMovieToText_{build_type.upper()}"
    run_cmd(
        "uv run pyinstaller --noconfirm --onedir --windowed "
        f'--name "{exe_name}" '
        '--icon "assets/icon.ico" '
        '--add-data "assets;assets" '
        "--collect-all whisper --collect-all tiktoken --collect-all flet --collect-data torch "
        "main.py"
    )

    print(f"\nBuild completed successfully!")
    print(f"Executable directory: dist/{exe_name}")


if __name__ == "__main__":
    main()
