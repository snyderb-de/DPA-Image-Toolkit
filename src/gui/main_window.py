"""
Main application window for DPA Image Toolkit.

Modern glass-morphism design with dark/light mode, operation state tracking,
and docked progress bars at bottom.
"""

import customtkinter as ctk
from .styles import get_theme, get_font, BUTTON_STYLE, PANEL_STYLE, TEXTBOX_STYLE


class MainWindow(ctk.CTk):
    """Main application window with modern aesthetic."""

    def __init__(self):
        """Initialize main window with all UI components."""
        super().__init__()

        # Window configuration
        self.title("DPA Image Toolkit")
        self.geometry("1000x700")
        self.minsize(900, 600)

        # State
        self.dark_mode = True
        self.current_theme = get_theme(self.dark_mode)
        self.current_panel = "menu"  # 'menu', 'auto_crop', 'tiff_merge'
        self.operation_in_progress = False
        self.operation_type = None  # 'crop' or 'merge'

        # Configure grid - 3 rows: toolbar, content, progress bar
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Build UI
        self._build_toolbar()
        self._build_content_area()
        self._build_progress_bar()

    def _build_toolbar(self):
        """Build top toolbar with buttons and theme toggle."""
        toolbar = ctk.CTkFrame(
            self,
            fg_color=self.current_theme["bg_secondary"],
            corner_radius=0,
            border_width=0,
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.grid_columnconfigure(2, weight=1)

        # App title / home button
        self.btn_home = ctk.CTkButton(
            toolbar,
            text="🏠 DPA Image Toolkit",
            font=get_font("heading"),
            height=BUTTON_STYLE["height"],
            corner_radius=BUTTON_STYLE["corner_radius"],
            fg_color="transparent",
            text_color=self.current_theme["fg_primary"],
            hover_color=self.current_theme["bg_tertiary"],
            command=self._on_home,
        )
        self.btn_home.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        # Spacer
        spacer = ctk.CTkFrame(toolbar, fg_color="transparent")
        spacer.grid(row=0, column=2, sticky="ew")

        # Theme Toggle (top-right)
        theme_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        theme_frame.grid(row=0, column=3, padx=16, pady=12, sticky="e")

        self.theme_label = ctk.CTkLabel(
            theme_frame,
            text="🌙",
            font=("Arial", 16),
            text_color=self.current_theme["fg_primary"],
        )
        self.theme_label.pack(side="left", padx=(0, 8))

        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="",
            command=self._toggle_theme,
            progress_color=self.current_theme["accent"],
        )
        self.theme_switch.pack(side="left")
        self.theme_switch.select()

    def _build_content_area(self):
        """Build main content area."""
        self.content = ctk.CTkFrame(
            self,
            fg_color=self.current_theme["bg_primary"],
            corner_radius=0,
        )
        self.content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Will hold either menu or active panel
        self.panel_container = ctk.CTkFrame(
            self.content,
            fg_color="transparent",
        )
        self.panel_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.panel_container.grid_rowconfigure(0, weight=1)
        self.panel_container.grid_columnconfigure(0, weight=1)

        # Show menu initially
        self._show_menu()

    def _build_progress_bar(self):
        """Build docked progress bar at bottom."""
        progress_frame = ctk.CTkFrame(
            self,
            fg_color=self.current_theme["bg_secondary"],
            corner_radius=0,
            border_width=0,
        )
        progress_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        progress_frame.grid_columnconfigure(1, weight=1)

        # Status label
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready",
            font=get_font("small"),
            text_color=self.current_theme["fg_secondary"],
            anchor="w",
        )
        self.progress_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=8)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            fg_color=self.current_theme["bg_tertiary"],
            progress_color=self.current_theme["accent"],
            height=4,
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 8))
        self.progress_bar.set(0)

    def _show_menu(self):
        """Show main menu."""
        # Clear container
        for widget in self.panel_container.winfo_children():
            widget.destroy()

        self.current_panel = "menu"

        # Menu panel
        menu_panel = ctk.CTkFrame(
            self.panel_container,
            fg_color=self.current_theme["bg_secondary"],
            corner_radius=12,
        )
        menu_panel.grid(row=0, column=0, padx=40, pady=40)
        menu_panel.grid_columnconfigure(0, minsize=300)

        # Title
        title = ctk.CTkLabel(
            menu_panel,
            text="DPA Image Toolkit",
            font=("Arial", 28, "bold"),
            text_color=self.current_theme["fg_primary"],
        )
        title.grid(row=0, column=0, pady=(40, 10))

        # Subtitle
        subtitle = ctk.CTkLabel(
            menu_panel,
            text="Image Processing & Organization",
            font=get_font("small"),
            text_color=self.current_theme["fg_tertiary"],
        )
        subtitle.grid(row=1, column=0, pady=(0, 40))

        # Auto Crop Button
        btn_crop = ctk.CTkButton(
            menu_panel,
            text="📷 Auto Crop Images",
            font=get_font("heading"),
            height=50,
            corner_radius=8,
            fg_color=self.current_theme["accent"],
            text_color="white",
            command=self._show_auto_crop_panel,
        )
        btn_crop.grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        # Merge TIFFs Button
        btn_merge = ctk.CTkButton(
            menu_panel,
            text="🔗 Merge TIFF Files",
            font=get_font("heading"),
            height=50,
            corner_radius=8,
            fg_color=self.current_theme["accent"],
            text_color="white",
            command=self._show_tiff_merge_panel,
        )
        btn_merge.grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        # Info text
        info = ctk.CTkLabel(
            menu_panel,
            text="Select a tool to get started",
            font=get_font("small"),
            text_color=self.current_theme["fg_tertiary"],
        )
        info.grid(row=4, column=0, pady=(40, 20))

    def _show_auto_crop_panel(self):
        """Show auto-crop panel."""
        if self.operation_in_progress:
            self._show_warning("Operation in progress", "Please wait for current operation to complete.")
            return

        # Clear container
        for widget in self.panel_container.winfo_children():
            widget.destroy()

        self.current_panel = "auto_crop"
        self._build_auto_crop_panel()

    def _show_tiff_merge_panel(self):
        """Show TIFF merge panel."""
        if self.operation_in_progress:
            self._show_warning("Operation in progress", "Please wait for current operation to complete.")
            return

        # Clear container
        for widget in self.panel_container.winfo_children():
            widget.destroy()

        self.current_panel = "tiff_merge"
        self._build_tiff_merge_panel()

    def _build_auto_crop_panel(self):
        """Build auto-crop panel."""
        from .auto_crop_panel import AutoCropPanel

        panel = AutoCropPanel(self)
        panel.build(self.panel_container)

    def _build_tiff_merge_panel(self):
        """Build TIFF merge panel."""
        from .tiff_merge_panel import TiffMergePanel

        panel = TiffMergePanel(self)
        panel.build(self.panel_container)

    def _on_home(self):
        """Handle home button click."""
        if self.operation_in_progress:
            self._show_confirmation(
                "Operation In Progress",
                "A file operation is currently running.\n\nAre you sure you want to go back to the menu?",
                self._show_menu,
            )
        else:
            self._show_menu()

    def _toggle_theme(self):
        """Toggle between dark and light mode."""
        self.dark_mode = not self.dark_mode
        self.current_theme = get_theme(self.dark_mode)
        self._refresh_theme()

    def _refresh_theme(self):
        """Refresh all UI components with current theme colors."""
        self.configure(fg_color=self.current_theme["bg_primary"])

        # Toolbar
        toolbar = self.grid_slaves(row=0)[0]
        toolbar.configure(fg_color=self.current_theme["bg_secondary"])
        self.btn_home.configure(
            text_color=self.current_theme["fg_primary"],
            hover_color=self.current_theme["bg_tertiary"],
        )
        self.theme_label.configure(text_color=self.current_theme["fg_primary"])
        self.theme_switch.configure(progress_color=self.current_theme["accent"])

        # Content
        content = self.grid_slaves(row=1)[0]
        content.configure(fg_color=self.current_theme["bg_primary"])

        # Progress bar frame
        progress_frame = self.grid_slaves(row=2)[0]
        progress_frame.configure(fg_color=self.current_theme["bg_secondary"])
        self.progress_label.configure(text_color=self.current_theme["fg_secondary"])
        self.progress_bar.configure(
            fg_color=self.current_theme["bg_tertiary"],
            progress_color=self.current_theme["accent"],
        )

        # Redraw current panel
        if self.current_panel == "menu":
            self._show_menu()
        elif self.current_panel == "auto_crop":
            self._show_auto_crop_panel()
        elif self.current_panel == "tiff_merge":
            self._show_tiff_merge_panel()

    def log_message(self, message, level="info"):
        """
        Add a message to the log display.

        Args:
            message (str): Message to log
            level (str): Log level ('info', 'success', 'warning', 'error')
        """
        if not hasattr(self, 'log_display'):
            return

        # Emojis by level
        emojis = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        emoji = emojis.get(level, "📝")

        # Format message
        formatted = f"{emoji} {message}\n"

        # Add to log (temporarily enable to append)
        self.log_display.configure(state="normal")
        self.log_display.insert("end", formatted)
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    def set_status(self, message, percentage=None):
        """
        Update status bar and progress bar.

        Args:
            message (str): Status message
            percentage (float): Progress 0-1, or None to hide
        """
        self.progress_label.configure(text=message)
        if percentage is not None:
            self.progress_bar.set(percentage)

    def _show_warning(self, title, message):
        """Show warning dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        label = ctk.CTkLabel(
            dialog,
            text=message,
            font=get_font("normal"),
            text_color=self.current_theme["fg_primary"],
            wraplength=350,
        )
        label.pack(pady=30, padx=20)

        btn = ctk.CTkButton(
            dialog,
            text="OK",
            command=dialog.destroy,
            fg_color=self.current_theme["accent"],
            text_color="white",
        )
        btn.pack(pady=10)

    def _show_confirmation(self, title, message, callback):
        """Show confirmation dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        label = ctk.CTkLabel(
            dialog,
            text=message,
            font=get_font("normal"),
            text_color=self.current_theme["fg_primary"],
            wraplength=350,
        )
        label.pack(pady=30, padx=20)

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        btn_yes = ctk.CTkButton(
            button_frame,
            text="Yes",
            command=lambda: (dialog.destroy(), callback()),
            fg_color=self.current_theme["accent"],
            text_color="white",
        )
        btn_yes.pack(side="left", padx=5)

        btn_no = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color=self.current_theme["bg_tertiary"],
            text_color=self.current_theme["fg_primary"],
        )
        btn_no.pack(side="left", padx=5)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
