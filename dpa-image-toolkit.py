"""
User-facing launcher script for DPA Image Toolkit.

This wrapper allows the app to be launched from a flat app folder such as:
    C:\\Users\\<user>\\Scripts\\dpa-img-tk\\
"""

from pathlib import Path
import sys


APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from main import main


if __name__ == "__main__":
    main()
