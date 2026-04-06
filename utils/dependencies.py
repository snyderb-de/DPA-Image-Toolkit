"""
Dependency checker for DPA Image Toolkit.

Verifies required packages are installed with human-friendly error messages.
"""

import sys


class DependencyChecker:
    """Check and report on missing dependencies."""

    def __init__(self):
        """Initialize checker."""
        self.missing = []
        self.versions = {}

    def check_all(self):
        """
        Check all required dependencies.

        Returns:
            tuple: (all_ok: bool, error_message: str or None)
        """
        dependencies = [
            ("customtkinter", "GUI Framework", "customtkinter"),
            ("PIL", "Image Processing", "Pillow"),
            ("cv2", "Computer Vision (Auto-crop)", "opencv-python"),
            ("numpy", "Numerical Computing", "numpy"),
        ]

        for module_name, description, pip_package in dependencies:
            if not self._check_package(module_name):
                self.missing.append((module_name, description, pip_package))

        if self.missing:
            error_msg = self._build_error_message()
            return False, error_msg

        return True, None

    def _check_package(self, module_name):
        """
        Check if a package is installed.

        Args:
            module_name (str): Module name to import

        Returns:
            bool: True if package found
        """
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "unknown")
            self.versions[module_name] = version
            return True
        except ImportError:
            return False

    def _build_error_message(self):
        """
        Build human-friendly error message.

        Returns:
            str: Formatted error message
        """
        lines = [
            "❌ DPA Image Toolkit - Missing Dependencies",
            "",
            "The following required components are not installed:",
            "",
        ]

        for module_name, description, _ in self.missing:
            lines.append(f"  • {description} ({module_name})")

        lines.extend([
            "",
            "What to do:",
            "  1. Open Command Prompt or PowerShell",
            "  2. Run this command:",
            "",
        ])

        # Build pip install command for the current Python interpreter
        pip_packages = []
        for _, _, pip_package in self.missing:
            if pip_package not in pip_packages:
                pip_packages.append(pip_package)
        packages = " ".join(pip_packages)
        lines.append(f"     \"{sys.executable}\" -m pip install {packages}")

        lines.extend([
            "",
            "If you continue to have problems:",
            "  → Contact support with this error message",
            f"  → Include your Python executable ({sys.executable})",
            "  → Include the error text from the installer",
            "",
        ])

        return "\n".join(lines)


def check_dependencies():
    """
    Check all dependencies and return status.

    Returns:
        tuple: (ok: bool, error_message: str or None)
    """
    checker = DependencyChecker()
    return checker.check_all()
