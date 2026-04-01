"""
Progress tracking for DPA Image Toolkit.

Provides callback system for tracking file and page progress during operations.
"""


class ProgressTracker:
    """Track progress of file and page operations."""

    def __init__(self, total_files=0, total_pages=0):
        """
        Initialize progress tracker.

        Args:
            total_files (int): Total files to process
            total_pages (int): Total pages to process
        """
        self.total_files = total_files
        self.total_pages = total_pages
        self.current_file = 0
        self.current_page = 0
        self.current_filename = ""

        # Callbacks
        self.on_file_progress = None
        self.on_page_progress = None
        self.on_status_update = None

    def set_total_files(self, count):
        """Set total file count."""
        self.total_files = count

    def set_total_pages(self, count):
        """Set total page count."""
        self.total_pages = count

    def start_file(self, filename):
        """
        Mark start of file processing.

        Args:
            filename (str): Name of file being processed
        """
        self.current_filename = filename
        self._trigger_status_update()

    def next_file(self):
        """Increment file counter."""
        self.current_file += 1
        self._trigger_file_progress()

    def next_page(self):
        """Increment page counter."""
        self.current_page += 1
        self._trigger_page_progress()

    def get_file_progress(self):
        """
        Get file progress.

        Returns:
            dict: {'current': int, 'total': int, 'percentage': float}
        """
        if self.total_files == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = (self.current_file / self.total_files) * 100
        return {
            "current": self.current_file,
            "total": self.total_files,
            "percentage": percentage,
        }

    def get_page_progress(self):
        """
        Get page progress.

        Returns:
            dict: {'current': int, 'total': int, 'percentage': float}
        """
        if self.total_pages == 0:
            return {"current": 0, "total": 0, "percentage": 0.0}

        percentage = (self.current_page / self.total_pages) * 100
        return {
            "current": self.current_page,
            "total": self.total_pages,
            "percentage": percentage,
        }

    def get_status(self):
        """
        Get current status message.

        Returns:
            str: Status message
        """
        if self.total_files == 0:
            return "Idle"

        if self.current_page > 0 and self.total_pages > 0:
            return (
                f"Processing: {self.current_file}/{self.total_files} files | "
                f"Page {self.current_page}/{self.total_pages}"
            )

        return f"Processing: {self.current_file}/{self.total_files} files"

    def reset(self):
        """Reset all counters."""
        self.current_file = 0
        self.current_page = 0
        self.current_filename = ""

    def _trigger_file_progress(self):
        """Call file progress callback if set."""
        if self.on_file_progress:
            progress = self.get_file_progress()
            self.on_file_progress(progress)

    def _trigger_page_progress(self):
        """Call page progress callback if set."""
        if self.on_page_progress:
            progress = self.get_page_progress()
            self.on_page_progress(progress)

    def _trigger_status_update(self):
        """Call status update callback if set."""
        if self.on_status_update:
            status = self.get_status()
            self.on_status_update(status)


def create_progress_callback(gui_window):
    """
    Create a progress callback for GUI updates.

    Args:
        gui_window: Main window with progress update methods

    Returns:
        ProgressTracker: Configured tracker
    """
    tracker = ProgressTracker()

    def update_progress(progress):
        """Update GUI with progress."""
        if hasattr(gui_window, "update_progress"):
            gui_window.update_progress(progress)

    def update_status(status):
        """Update GUI with status."""
        if hasattr(gui_window, "set_status"):
            gui_window.set_status(status)

    tracker.on_file_progress = update_progress
    tracker.on_page_progress = update_progress
    tracker.on_status_update = update_status

    return tracker
