<#
JPEG Resizer (text-safe) + Original Mover
- Recursively scans a root folder for .jpg/.jpeg files
- Creates resized “replacement” JPEGs IN PLACE (same folder, same filename), with:
    - Max width: 2000px (only downscale; never upscale)
    - DPI metadata set to 96 PPI
    - Quality 85
    - 4:4:4 sampling (important for crisp text)
    - Strips metadata on the resized outputs
- Also generates sidecar derivatives in the SAME folder:
    - _thumb  (600px max width)
    - _med    (1200px max width)
    - _lg     (2000px max width)  [same as replacement width, but separate file]
- Moves the ORIGINAL (pre-resize) JPEG into:
    <RootPath>\_ORIGINAL_JPEGS\
- Skips scanning anything inside the backup folder
- Supports -WhatIf / -Confirm

Why this preserves “archival integrity”:
- The pre-resize originals are preserved (moved to backup folder).
- The in-place files become your access copies (smaller, screen-friendly).
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$RootPath,

  [int]$Dpi = 96,
  [int]$Quality = 85,

  [int]$MaxWidthReplace = 2000,  # replacement (same filename) max width
  [int]$ThumbWidth = 600,
  [int]$MedWidth = 1200,
  [int]$LgWidth = 2000,

  [string]$BackupFolderName = "_ORIGINAL_JPEGS"
)

# --- Preconditions ---
$magick = Get-Command magick -ErrorAction SilentlyContinue
if (-not $magick) {
  throw "ImageMagick not found. Install it and ensure 'magick' is on PATH."
}

if (-not (Test-Path -LiteralPath $RootPath)) {
  throw "RootPath does not exist: $RootPath"
}

$RootPath = (Resolve-Path -LiteralPath $RootPath).Path
$BackupDir = Join-Path $RootPath $BackupFolderName

function Ensure-Directory {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    if ($PSCmdlet.ShouldProcess($Path, "Create Directory")) {
      New-Item -ItemType Directory -Path $Path -Force | Out-Null
    } else {
      Write-Host "[WhatIf] Would create directory: $Path"
    }
  }
}

function Get-UniqueMovePath {
  param(
    [Parameter(Mandatory=$true)][string]$DestDir,
    [Parameter(Mandatory=$true)][string]$FileName
  )

  $candidate = Join-Path $DestDir $FileName
  if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }

  $base = [System.IO.Path]::GetFileNameWithoutExtension($FileName)
  $ext  = [System.IO.Path]::GetExtension($FileName)

  $i = 1
  while ($true) {
    $try = Join-Path $DestDir ("{0}__dup{1}{2}" -f $base, $i, $ext)
    if (-not (Test-Path -LiteralPath $try)) { return $try }
    $i++
  }
}

function Render-Jpeg {
  param(
    [Parameter(Mandatory=$true)][string]$In,
    [Parameter(Mandatory=$true)][string]$Out,
    [Parameter(Mandatory=$true)][int]$MaxWidth
  )

  # Only shrink if larger than target width: "${MaxWidth}x>"
  # 4:4:4 sampling is key for text edges
  & magick "$In" `
    -resize ("{0}x>" -f $MaxWidth) `
    -units PixelsPerInch -density $Dpi `
    -sampling-factor 4:4:4 `
    -quality $Quality `
    -strip `
    "$Out"

  return $LASTEXITCODE
}

# --- Counters ---
[int]$TotalJpegsScanned = 0
[int]$SkippedBackupFolder = 0
[int]$ReplacementPlanned = 0
[int]$ReplacementWritten = 0
[int]$ThumbWritten = 0
[int]$MedWritten = 0
[int]$LgWritten = 0
[int]$MovedOriginals = 0
[int]$SkippedNoOp = 0
[int]$Failures = 0

Write-Host "== JPEG Resizer + Mover =="
Write-Host "Root folder: $RootPath"
Write-Host "Backup folder (excluded from scan): $BackupDir"
Write-Host "Replace max width: $MaxWidthReplace"
Write-Host "Derivatives: thumb=$ThumbWidth, med=$MedWidth, lg=$LgWidth"
Write-Host "Quality: $Quality | DPI: $Dpi | Sampling: 4:4:4"
Write-Host "Dry-run mode: $($WhatIfPreference)"
Write-Host ""

Ensure-Directory -Path $BackupDir

Write-Host "Scanning folder tree..."

Get-ChildItem -LiteralPath $RootPath -Recurse -File |
  Where-Object {
    $_.Extension -match '^\.(jpg|jpeg)$' -and
    $_.FullName -notlike "$BackupDir\*"
  } |
  ForEach-Object {

    $TotalJpegsScanned++

    $src  = $_.FullName
    $dir  = $_.DirectoryName
    $name = $_.Name
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext  = [System.IO.Path]::GetExtension($name)

    Write-Host ""
    Write-Host "Scanning file: $src"

    # Sidecar derivative names (same folder)
    $thumbOut = Join-Path $dir ("{0}_thumb{1}" -f $base, $ext)
    $medOut   = Join-Path $dir ("{0}_med{1}"   -f $base, $ext)
    $lgOut    = Join-Path $dir ("{0}_lg{1}"    -f $base, $ext)

    # Temp file for replacement to avoid clobbering input mid-process
    $tmpReplace = Join-Path $dir ("{0}.__tmp_resize__{1}" -f $base, $ext)

    # If replacement and derivatives already exist, you may want to skip.
    # We’ll be conservative: skip only if all three derivatives exist AND
    # the original has already been moved (i.e., src is not present). But src is present here.
    # So we proceed, unless you want a stricter skip rule.
    $ReplacementPlanned++

    # 1) Create replacement temp + derivatives (reads from current src)
    if ($PSCmdlet.ShouldProcess($src, "Render replacement + derivatives")) {

      # Replacement temp
      Write-Host "Found JPEG. Creating replacement (max width $MaxWidthReplace) in-place..."
      if (Test-Path -LiteralPath $tmpReplace) { Remove-Item -LiteralPath $tmpReplace -Force -ErrorAction SilentlyContinue }

      $rc = Render-Jpeg -In $src -Out $tmpReplace -MaxWidth $MaxWidthReplace
      if ($rc -ne 0 -or -not (Test-Path -LiteralPath $tmpReplace)) {
        $Failures++
        Write-Warning "Replacement render failed (leaving original untouched)."
        return
      }

      # Derivatives (write/overwrite)
      Write-Host "Creating derivatives in same folder..."
      $rc1 = Render-Jpeg -In $src -Out $thumbOut -MaxWidth $ThumbWidth
      if ($rc1 -ne 0) { $Failures++; Write-Warning "Thumb render failed." } else { $ThumbWritten++ }

      $rc2 = Render-Jpeg -In $src -Out $medOut -MaxWidth $MedWidth
      if ($rc2 -ne 0) { $Failures++; Write-Warning "Medium render failed." } else { $MedWritten++ }

      $rc3 = Render-Jpeg -In $src -Out $lgOut -MaxWidth $LgWidth
      if ($rc3 -ne 0) { $Failures++; Write-Warning "Large render failed." } else { $LgWritten++ }

      # 2) Move original to backup folder
      $dest = Get-UniqueMovePath -DestDir $BackupDir -FileName $name
      Write-Host "Moving original to backup folder..."
      try {
        Move-Item -LiteralPath $src -Destination $dest -Force
        $MovedOriginals++
        Write-Host "Moved original -> $dest"
      }
      catch {
        $Failures++
        Write-Warning "Failed moving original. Removing temp replacement to avoid loss."
        Remove-Item -LiteralPath $tmpReplace -Force -ErrorAction SilentlyContinue
        return
      }

      # 3) Promote temp replacement into original location/name
      Write-Host "Placing resized replacement back into original location..."
      try {
        Move-Item -LiteralPath $tmpReplace -Destination $src -Force
        $ReplacementWritten++
        Write-Host "Replacement complete."
      }
      catch {
        $Failures++
        Write-Warning "Failed placing replacement. Original is in backup: $dest"
        # tmp remains; try to keep it for recovery
        return
      }
    }
    else {
      Write-Host "[WhatIf] Would render replacement temp -> $tmpReplace"
      Write-Host "[WhatIf] Would render derivatives -> $thumbOut | $medOut | $lgOut"
      Write-Host "[WhatIf] Would move original -> $BackupDir"
      Write-Host "[WhatIf] Would place resized replacement back -> $src"
    }
  }

Write-Host ""
Write-Host "== Summary =="
Write-Host ("Total JPEGs scanned:       {0}" -f $TotalJpegsScanned)
Write-Host ("Replacements planned:      {0}" -f $ReplacementPlanned)
Write-Host ("Replacements completed:    {0}" -f $ReplacementWritten)
Write-Host ("Derivatives completed:     thumb={0}  med={1}  lg={2}" -f $ThumbWritten, $MedWritten, $LgWritten)
Write-Host ("Originals moved to backup: {0}" -f $MovedOriginals)
Write-Host ("Failures:                  {0}" -f $Failures)
Write-Host ""
Write-Host "Done."
