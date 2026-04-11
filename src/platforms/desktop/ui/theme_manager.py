import flet as ft


class ThemeManager:
    # Colors inspired by Windows 11 / Slate / Zinc
    BACKGROUND = "#111111"  # Deep Zinc
    SURFACE = "#1E1E1E"  # Lighter Zinc
    ACCENT = "#0078D4"  # Windows Blue
    ACCENT_LIGHT = "#47A1EB"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A1A1AA"
    BORDER = "#2E2E2E"

    @staticmethod
    def apply_theme(page: ft.Page):
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = ThemeManager.BACKGROUND

        # Windows 11 specific font if available
        page.theme = ft.Theme(
            color_scheme_seed=ThemeManager.ACCENT,
            font_family="Segoe UI Variable",
            visual_density=ft.VisualDensity.COMPACT,
            page_transitions=ft.PageTransitionsTheme(
                windows=ft.PageTransitionTheme.ZOOM,
                android=ft.PageTransitionTheme.ZOOM,
                ios=ft.PageTransitionTheme.CUPERTINO,
            ),
            navigation_rail_theme=ft.NavigationRailTheme(
                unselected_label_text_style=ft.TextStyle(size=11, color=ThemeManager.TEXT_SECONDARY),
                selected_label_text_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ThemeManager.ACCENT),
                label_type=ft.NavigationRailLabelType.SELECTED,
            ),
        )

        # Configure window properties for a native feel
        page.window_bgcolor = ft.Colors.TRANSPARENT
        page.window_title_bar_buttons_icon_color = ThemeManager.TEXT_PRIMARY

        # Update styling tokens
        page.update()

    @staticmethod
    def get_container_style():
        return {
            "bgcolor": ThemeManager.SURFACE,
            "border_radius": 12,
            "border": ft.border.all(1, ThemeManager.BORDER),
            "padding": 20,
        }

    @staticmethod
    def get_glass_style():
        return {
            "bgcolor": ft.Colors.with_opacity(0.1, ThemeManager.SURFACE),
            "blur": 20,
            "border_radius": 16,
            "border": ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.WHITE)),
        }
