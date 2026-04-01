# TIFF Combine Naming Validation Module

## Overview

The `naming.py` module handles all file naming validation for tiff-combine operations. It ensures files follow the exact pattern required by the merge algorithm.

## File Naming Pattern

**Required Pattern**: `[groupname]_###.tif`

- `[groupname]`: Any text (can contain underscores)
- `_`: Single underscore (separator)
- `###`: Exactly 3 digits (001-999)
- `.tif`: File extension

### ⚠️ Important Limitations

This tool is designed for bundling images into multi-page TIFF files for organizational purposes. However:

- **Maximum 999 pages per document** (3-digit limit: 001-999)
- **Not recommended for excessively large multi-page TIFFs** - be mindful of file size
- Large TIFF files can become slow to load and process in standard image viewers
- Consider keeping multi-page TIFFs under 100-200 pages for practical use

**Use Case**: Organize scanned documents, batch images, or related photos into single TIFF files for easier storage and distribution. Not intended for creating massive archives.

## Examples

### ✅ Valid Names

```
document_001.tif     → group: "document"
document_002.tif     → same group, next page
report_page_001.tif  → group: "report_page" (underscore in name)
report_page_042.tif  → group: "report_page", page 42
scan_001.tif         → group: "scan"
my_doc_text_001.tif  → group: "my_doc_text"
```

### ❌ Invalid Names

```
document_1.tif       ✗ Only 1 digit (needs 3)
document_01.tif      ✗ Only 2 digits (needs 3)
document_0001.tif    ✗ 4 digits (needs 3)
document.tif         ✗ No sequence
001_document.tif     ✗ Sequence in wrong position
doc_001_final.tif    ✗ Sequence not at end
```

## API Reference

### validate_file_naming()

Check if a single file follows the naming pattern.

```python
from modules.tiff_combine.naming import validate_file_naming

result = validate_file_naming('document_001.tif')  # True
result = validate_file_naming('document_1.tif')    # False
```

**Returns**: `bool`

### extract_group_name()

Get the group name from a filename.

```python
from modules.tiff_combine.naming import extract_group_name

group = extract_group_name('document_001.tif')     # "document"
group = extract_group_name('report_page_042.tif')  # "report_page"
group = extract_group_name('invalid_name.tif')     # "invalid_name"
```

**Returns**: `str`

### extract_sequence_number()

Get the sequence number from a filename.

```python
from modules.tiff_combine.naming import extract_sequence_number

seq = extract_sequence_number('document_001.tif')   # 1
seq = extract_sequence_number('document_042.tif')   # 42
seq = extract_sequence_number('invalid_name.tif')   # None
```

**Returns**: `int|None`

### detect_groups()

Detect all groups in a folder and return grouped, sorted files.

```python
from modules.tiff_combine.naming import detect_groups
from pathlib import Path

groups = detect_groups(Path('my_folder'))
# Returns:
# {
#   'document': ['document_001.tif', 'document_002.tif', 'document_003.tif'],
#   'scan': ['scan_001.tif', 'scan_002.tif']
# }
```

**Returns**: `dict[str, list[str]]` - Files are automatically sorted by sequence

### validate_naming_convention()

Comprehensive validation of all .tif files in a folder.

```python
from modules.tiff_combine.naming import validate_naming_convention
from pathlib import Path

groups, is_valid, issues = validate_naming_convention(Path('my_folder'))

if is_valid:
    print(f"✓ Valid - Found {len(groups)} groups")
    for group_name, files in groups.items():
        print(f"  {group_name}: {len(files)} files")
else:
    print(f"✗ Invalid - {len(issues)} problems found:")
    for issue in issues:
        print(f"  {issue}")
```

**Returns**: `tuple(dict, bool, list)`
- `groups`: `{'group': ['file1', 'file2'], ...}`
- `is_valid`: `True` if all .tif files follow pattern
- `issues`: List of problem files/error messages

### get_validation_summary()

Get structured summary for UI display.

```python
from modules.tiff_combine.naming import get_validation_summary
from pathlib import Path

summary = get_validation_summary(Path('my_folder'))

# Returns:
# {
#   'is_valid': True,
#   'groups': {...},
#   'group_count': 2,
#   'file_count': 5,
#   'issues': [],
#   'issue_count': 0,
#   'group_details': {
#     'document': {
#       'count': 3,
#       'files': ['document_001.tif', 'document_002.tif', 'document_003.tif'],
#       'first': 'document_001.tif',
#       'last': 'document_003.tif'
#     },
#     ...
#   }
# }
```

**Returns**: `dict` - Ready to display in UI

## Usage in UI (Week 5)

### Example: Validation Panel

```python
from modules.tiff_combine.naming import get_validation_summary

# When user selects folder:
summary = get_validation_summary(selected_folder)

if summary['is_valid']:
    # Show groups
    for group_name, details in summary['group_details'].items():
        print(f"✓ {group_name}: {details['count']} files")
        for file in details['files']:
            print(f"  - {file}")

    # Enable "Proceed" button
    proceed_button.enable()
else:
    # Show errors
    for issue in summary['issues']:
        print(f"✗ {issue}")

    # Disable "Proceed" button
    proceed_button.disable()
```

## Regex Pattern

The module uses this regex to validate and extract:

```python
# Validation pattern - file must match this
pattern = r'_\d{3}\.tif$'  # Case-insensitive

# Extraction pattern - remove this to get group name
pattern = r'_\d{3}$'       # Case-insensitive
```

## Integration Notes

- **Week 5**: This module will be called by `tiff_merge_panel.py`
- **Week 5**: Error handling will use results to decide if merge can proceed
- **Week 5**: UI will display validation summary before allowing merge
- **Critical**: User must explicitly confirm naming is correct before merge starts

## Testing

```bash
# Test individual functions
python -c "from modules.tiff_combine.naming import validate_file_naming; print(validate_file_naming('test_001.tif'))"

# Test in interactive mode
python
>>> from modules.tiff_combine.naming import *
>>> validate_file_naming('document_001.tif')
True
>>> extract_group_name('document_001.tif')
'document'
>>> extract_sequence_number('document_042.tif')
42
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Invalid naming: file.tif" | Wrong pattern | Rename to `name_001.tif` |
| Group not detected | Underscores in name? | Should work - check pattern |
| Files not sorted correctly | Sequence numbers odd | Must be exactly 3 digits |
| All files marked invalid | Case-sensitive? | Extension is case-insensitive ✓ |

## Performance

- File detection: O(n) where n = number of files
- Sorting: O(n log n) by sequence number
- Typical: < 100ms for 1000 files

## Future Enhancements

- [ ] Support for custom naming patterns
- [ ] Warnings for gaps in sequences
- [ ] Auto-renaming tools
- [ ] Batch operations
