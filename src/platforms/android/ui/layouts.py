import flet as ft

def MobileLayout(content: ft.Control, title: str = "MTT Mobile", nav_bar: ft.NavigationBar = None):
    """
    Common layout wrapper for mobile views.
    Ensures consistent look and feel with a Material 3 style.
    """
    return ft.View(
        route="/",
        appbar=ft.AppBar(
            title=ft.Text(title, weight=ft.FontWeight.BOLD, size=20),
            bgcolor=ft.Colors.SURFACE_VARIANT,
            center_title=True,
            actions=[
                ft.IconButton(ft.Icons.SETTINGS_OUTLINED, icon_size=20),
            ],
        ),
        navigation_bar=nav_bar,
        controls=[
            ft.Container(
                content=content,
                expand=True,
                padding=ft.padding.all(15),
            )
        ],
        bgcolor=ft.Colors.BACKGROUND,
    )
