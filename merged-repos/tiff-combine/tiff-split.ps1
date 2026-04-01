<#
TIFF Splitter
- Recursively scans a root folder for .tif/.tiff files
- Leaves single-page TIFFs alone
- Splits multi-page TIFFs into single-page TIFFs named: OriginalName_1.tif, OriginalName_2.tif, ...
- Writes split output next to the original file
- Moves the original multi-page TIFF into: <RootPath>\_ORIGINAL_MULTIPAGE_TIFFS\
- Skips scanning anything inside the backup folder
- Supports -WhatIf (dry-run) and -Confirm via SupportsShouldProcess

End summary:
- Total TIFFs scanned
- Single-page TIFFs
- Multi-page TIFFs
- Multi-page split attempted (or would be attempted under -WhatIf)
- Originals moved (or would be moved under -WhatIf)

Requires:
- ImageMagick CLI available as: magick
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$RootPath
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

# Folder to hold originals so you can delete in one shot later
$OriginalsDirName = "_ORIGINAL_MULTIPAGE_TIFFS"
$OriginalsDir = Join-Path $RootPath $OriginalsDirName

# --- Counters for summary ---
[int]$TotalTiffsScanned = 0
[int]$SinglePageTiffs   = 0
[int]$MultiPageTiffs    = 0
[int]$SplitsPlanned     = 0   # split executed OR would execute in -WhatIf
[int]$MovesPlanned      = 0   # move executed OR would execute in -WhatIf
[int]$SplitsFailed      = 0
[int]$MovesFailed       = 0
[int]$AlreadySplitSkip  = 0   # multi-page where outputs existed; still moved/or would move

function Ensure-Directory {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    if ($PSCmdlet.ShouldProcess($Path, "Create Directory")) {
      New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    else {
      Write-Host "[WhatIf] Would create directory: $Path"
    }
  }
}

function Get-TiffPageCount {
  param([Parameter(Mandatory = $true)][string]$Path)

  # ImageMagick prints %n once per frame for multi-page TIFFs (e.g., 3 pages -> "3\n3\n3\n").
  # We take the first line only to get the real page count.
  $out = & magick identify -quiet -format "%n`n" -- "$Path" 2>$null |
    Select-Object -First 1

  if (-not $out) { return 0 }

  $s = $out.ToString().Trim()
  if ($s -notmatch '^\d+$') { return 0 }
  [int]$s
}

function Get-UniqueMovePath {
  param(
    [Parameter(Mandatory = $true)][string]$DestDir,
    [Parameter(Mandatory = $true)][string]$FileName
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

Write-Host "== TIFF Splitter =="
Write-Host "Root folder: $RootPath"
Write-Host "Backup folder (excluded from scan): $OriginalsDir"
Write-Host "Dry-run mode: $($WhatIfPreference)"
Write-Host ""
Write-Host "Scanning folder tree..."

# Enumerate all TIFFs except those inside the backup folder
Get-ChildItem -LiteralPath $RootPath -Recurse -File |
  Where-Object {
    $_.Extension -match '^\.(tif|tiff)$' -and
    $_.FullName -notlike "$OriginalsDir\*"
  } |
  ForEach-Object {

    $TotalTiffsScanned++

    $src  = $_.FullName
    $dir  = $_.DirectoryName
    $base = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)

    Write-Host ""
    Write-Host "Scanning file: $src"

    $pages = Get-TiffPageCount -Path $src
    if ($pages -le 0) {
      Write-Warning "Could not read page count (skipping)"
      return
    }

    if ($pages -eq 1) {
      $SinglePageTiffs++
      Write-Host "Found: single-page TIFF (left alone)."
      return
    }

    $MultiPageTiffs++
    Write-Host "Found: multi-page TIFF ($pages pages)."

    # Expected outputs for idempotence
    $expected = 1..$pages | ForEach-Object {
      Join-Path $dir ("{0}_{1}.tif" -f $base, $_)
    }

    $allExist = $true
    foreach ($p in $expected) {
      if (-not (Test-Path -LiteralPath $p)) { $allExist = $false; break }
    }

    if (-not $allExist) {
      Write-Host "Plan: split into $pages files in: $dir"
      $pattern = Join-Path $dir ("{0}_%d.tif" -f $base)

      $SplitsPlanned++

      if ($PSCmdlet.ShouldProcess($src, "Split into $pages single-page TIFFs")) {
        Write-Host "Splitting..."
        & magick "$src" -scene 1 "$pattern"

        if ($LASTEXITCODE -ne 0) {
          $SplitsFailed++
          Write-Warning "Split failed (original NOT moved)."
          return
        }

        Write-Host "Split complete."
      }
      else {
        Write-Host "[WhatIf] Would split -> $pattern"
      }
    }
    else {
      $AlreadySplitSkip++
      Write-Host "Outputs already exist (_1.._$pages). Skipping split."
    }

    # Ensure backup folder exists (respecting -WhatIf)
    Ensure-Directory -Path $OriginalsDir

    # Move original multipage TIFF to the originals folder
    $dest = Get-UniqueMovePath -DestDir $OriginalsDir -FileName $_.Name
    Write-Host "Plan: move original -> $dest"

    $MovesPlanned++

    if ($PSCmdlet.ShouldProcess($src, "Move original to backup folder")) {
      Write-Host "Moving original..."
      try {
        Move-Item -LiteralPath $src -Destination $dest -Force
        Write-Host "Moved."
      }
      catch {
        $MovesFailed++
        Write-Warning "Failed moving original: $($_.Exception.Message)"
      }
    }
    else {
      Write-Host "[WhatIf] Would move original -> $dest"
    }
  }

Write-Host ""
Write-Host "== Summary =="
Write-Host ("Total TIFFs scanned:            {0}" -f $TotalTiffsScanned)
Write-Host ("Single-page TIFFs:              {0}" -f $SinglePageTiffs)
Write-Host ("Multi-page TIFFs:               {0}" -f $MultiPageTiffs)
Write-Host ("Multi-page TIFFs skipped split: {0} (outputs already existed)" -f $AlreadySplitSkip)
Write-Host ("Splits planned:                 {0}" -f $SplitsPlanned)
Write-Host ("Moves planned:                  {0}" -f $MovesPlanned)
Write-Host ("Splits failed:                  {0}" -f $SplitsFailed)
Write-Host ("Moves failed:                   {0}" -f $MovesFailed)
Write-Host ""
Write-Host "Done."
