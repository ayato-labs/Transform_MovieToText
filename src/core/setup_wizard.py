import importlib
import subprocess

import flet as ft

# List of heavy dependencies that should be installed on-demand
HEAVY_DEPS = ["faster-whisper", "torch", "torchvision", "torchaudio", "fastembed", "opencv-python"]


def is_env_ready():
    """Check if all heavy dependencies are available."""
    missing = []
    for dep in HEAVY_DEPS:
        # Convert package name to import name (e.g., faster-whisper -> faster_whisper)
        import_name = dep.replace("-", "_")
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(dep)
    return missing


class SetupWizard(ft.UserControl):
    def __init__(self, missing_deps, on_complete):
        super().__init__()
        self.missing_deps = missing_deps
        self.on_complete = on_complete
        self.progress_bar = ft.ProgressBar(width=400, value=0)
        self.status_text = ft.Text("Initializing setup...", size=14)
        self.log_text = ft.Text("", size=12, color="grey")

    def build(self):
        return ft.Column(
            [
                ft.Text("Welcome to Transform MovieToText", size=24, weight="bold"),
                ft.Text("To enable AI transcription, some additional components need to be downloaded (approx. 2-3 GB).", size=16),
                ft.Divider(),
                ft.Text(f"Missing: {', '.join(self.missing_deps)}", color="blue", weight="bold"),
                self.status_text,
                self.progress_bar,
                self.log_text,
                ft.ElevatedButton("Start Download & Setup", on_click=self.start_setup, icon=ft.icons.DOWNLOAD),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        )

    def start_setup(self, e):
        e.control.disabled = True
        self.update()

        # In a real scenario, we would run 'uv pip install' via subprocess
        # Here we simulate the process for the UI prototype
        self.status_text.value = "Installing components via 'uv'..."
        self.progress_bar.value = None  # Indeterminate
        self.update()

        try:
            # Command to install via uv (assuming uv is in environment)
            cmd = ["uv", "pip", "install"] + self.missing_deps
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

            for line in process.stdout:
                self.log_text.value = line.strip()
                self.update()

            process.wait()

            if process.returncode == 0:
                self.status_text.value = "Setup completed successfully!"
                self.status_text.color = "green"
                self.progress_bar.value = 1
                self.update()
                # Notify completion (UI will show a restart button)
                self.on_complete()
            else:
                self.status_text.value = f"Setup failed with code {process.returncode}."
                self.status_text.color = "red"
                self.update()

        except Exception as ex:
            self.status_text.value = f"Error: {str(ex)}"
            self.status_text.color = "red"
            self.update()


def main(page: ft.Page):
    page.title = "Transform MovieToText - Setup Wizard"
    page.window_width = 600
    page.window_height = 500
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    missing = is_env_ready()

    def on_complete():
        page.add(ft.Text("Please restart the application to use all features.", color="orange", weight="bold"))
        page.add(ft.ElevatedButton("Close App", on_click=lambda _: page.window_close()))

    if not missing:
        page.add(ft.Text("All components are ready! Close this window and start the app.", color="green"))
    else:
        page.add(SetupWizard(missing, on_complete))


if __name__ == "__main__":
    ft.app(target=main)
