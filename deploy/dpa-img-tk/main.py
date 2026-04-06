"""
DPA Image Toolkit - Main Entry Point

Unified GUI application for auto-cropping and TIFF merging operations.
"""

import sys
from pathlib import Path

# Add app root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.dependencies import check_dependencies


def main():
    """Run the application."""
    # Check dependencies first
    ok, error_msg = check_dependencies()

    if not ok:
        # Show error in console
        print("\n" + "=" * 60)
        print(error_msg)
        print("=" * 60 + "\n")

        # Try to show error dialog if customtkinter is available
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "DPA Image Toolkit - Missing Dependencies",
                error_msg,
            )
            root.destroy()
        except Exception:
            pass

        sys.exit(1)

    # All dependencies OK - import GUI
    from gui import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
