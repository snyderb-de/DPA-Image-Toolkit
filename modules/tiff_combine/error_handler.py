"""
Error handling for tiff-combine operations.

Manages failed files, generates error reports, and maintains error folder.
"""

from pathlib import Path
import shutil
from datetime import datetime
from utils.log_utils import log_message


class ErrorHandler:
    """Manage errors during TIFF operations."""

    def __init__(self, error_folder):
        """
        Initialize error handler.

        Args:
            error_folder (Path|str): Path to errored-files/ folder
        """
        self.error_folder = Path(error_folder)
        self.errors = []

        # Create folder if needed
        self.error_folder.mkdir(parents=True, exist_ok=True)

    def add_error(self, filename, error_message, source_file=None):
        """
        Record an error.

        Args:
            filename (str): Name of file that failed
            error_message (str): Error description
            source_file (Path|str): Path to source file
        """
        error_record = {
            "filename": filename,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "source_file": str(source_file) if source_file else None,
        }
        self.errors.append(error_record)
        log_message(f"Error recorded: {filename} - {error_message}", "error")

    def move_file_to_error_folder(self, source_file):
        """
        Move a file to error folder.

        Args:
            source_file (Path|str): File to move

        Returns:
            bool: True if moved successfully
        """
        source_file = Path(source_file)

        if not source_file.is_file():
            log_message(f"File not found: {source_file}", "warning")
            return False

        try:
            dest_file = self.error_folder / source_file.name
            shutil.move(str(source_file), str(dest_file))
            log_message(f"Moved to error folder: {source_file.name}", "warning")
            return True
        except Exception as e:
            log_message(f"Failed to move {source_file.name}: {e}", "error")
            return False

    def generate_error_report(self, output_file=None):
        """
        Generate error report.

        Args:
            output_file (Path|str): Path to save report (default: errored-files/ERROR_REPORT.txt)

        Returns:
            str: Report content
        """
        if not output_file:
            output_file = self.error_folder / "ERROR_REPORT.txt"

        report_lines = [
            "DPA Image Toolkit - Error Report",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Errors: {len(self.errors)}",
            "",
            "Details:",
            "-" * 50,
        ]

        for i, error in enumerate(self.errors, 1):
            report_lines.append(f"\n{i}. {error['filename']}")
            report_lines.append(f"   Error: {error['error']}")
            report_lines.append(f"   Time: {error['timestamp']}")
            if error['source_file']:
                report_lines.append(f"   Source: {error['source_file']}")

        report_lines.append("\n" + "=" * 50)
        report_lines.append("Please review the files in this folder.")
        report_lines.append("Correct issues and retry the operation.")

        report_content = "\n".join(report_lines)

        # Save to file
        try:
            Path(output_file).write_text(report_content)
            log_message(f"Error report saved: {output_file}", "info")
        except Exception as e:
            log_message(f"Failed to save error report: {e}", "error")

        return report_content

    def get_error_summary(self):
        """
        Get summary of errors.

        Returns:
            dict: Error statistics
        """
        return {
            "total_errors": len(self.errors),
            "files_with_errors": [e["filename"] for e in self.errors],
            "error_messages": [e["error"] for e in self.errors],
        }

    def has_errors(self):
        """Check if any errors were recorded."""
        return len(self.errors) > 0
