Testing Assets
==============

This folder collects per-tool test suites for the DPA Image Toolkit.

Layout
------

- `auto_crop/` - generator + test runner for Auto Crop
- `tiff_merge/` - generator + test runner for TIFF Merge
- `tiff_split/` - generator + test runner for TIFF Split
- `add_border/` - generator + test runner for Add Border
- `ocr_pdf/` - generator + test runner for OCR to PDF
- `shared/` - shared helper tests that are not tied to a single tool

Run From Repo Root
------------------

- `python3 testing/auto_crop/test_auto_crop.py`
- `python3 testing/tiff_merge/test_tiff_merge.py`
- `python3 -m unittest testing.tiff_split.test_tiff_split`
- `python3 -m unittest testing.add_border.test_add_border`
- `python3 -m unittest testing.ocr_pdf.test_ocr_pdf`
- `python3 -m unittest testing.shared.test_tool_dependencies`

Notes
-----

- Each tool owns its own `generate_fixtures.py` and `test_*.py`.
- Generated fixtures and outputs stay local and are ignored by Git.
- Personal scratch data or machine-only sample sets should live under `testing/local/`.
