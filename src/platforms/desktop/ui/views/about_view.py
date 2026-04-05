import flet as ft


class AboutView(ft.Column):
    """
    About the application.
    """

    def __init__(self):
        super().__init__(expand=True, horizontal_alignment="center", spacing=10)

        self.controls = [
            ft.Icon(ft.Icons.INFO, size=50, color="blue"),
            ft.Text("Transform MovieToText", size=32, weight="bold"),
            ft.Text("Version 1.0.0 (Refactored)", size=16, italic=True),
            ft.Divider(),
            ft.Text("An AI-powered video/audio to text converter."),
            ft.Text("Supports local Whisper processing and AI-driven minutes generation."),
            ft.Text("© 2026 Ayato-AI-for-Auto", size=12, color="grey"),
        ]
