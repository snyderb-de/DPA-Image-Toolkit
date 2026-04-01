"""
Dependency checker for DPA Image Toolkit.

Verifies required packages are installed with human-friendly error messages.
"""

import sys
from pathlib import Path


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
            ("customtkinter", "GUI Framework"),
            ("PIL", "Image Processing"),
            ("cv2", "Computer Vision (Auto-crop)"),
            ("numpy", "Numerical Computing"),
        ]

        for package_name, description in dependencies:
            if not self._check_package(package_name, description):
                self.missing.append((package_name, description))

        if self.missing:
            error_msg = self._build_error_message()
            return False, error_msg

        return True, None

    def _check_package(self, package_name, description):
        """
        Check if a package is installed.

        Args:
            package_name (str): Package name to import
            description (str): Human-readable description

        Returns:
            bool: True if package found
        """
        try:
            module = __import__(package_name)
            version = getattr(module, "__version__", "unknown")
            self.versions[package_name] = version
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

        for package_name, description in self.missing:
            lines.append(f"  • {description} ({package_name})")

        lines.extend([
            "",
            "What to do:",
            "  1. Open Command Prompt or PowerShell",
            "  2. Run this command:",
            "",
        ])

        # Build pip install command
        packages = " ".join([pkg[0] for pkg in self.missing])
        lines.append(f"     pip install {packages}")

        lines.extend([
            "",
            "If you continue to have problems:",
            "  → Contact support with this error message",
            "  → Include your Python version (python --version)",
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
