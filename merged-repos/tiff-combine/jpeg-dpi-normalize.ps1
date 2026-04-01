<#
JPEG DPI Normalizer (IrfanView)

- Recursively scans a root folder for .jpg/.jpeg
- Sets DPI metadata to 96x96 using IrfanView
- Does NOT resize
- Does NOT change pixel dimensions
- Does NOT change quality
- Overwrites files in place
- Supports -WhatIf

Requires:
IrfanView installed at:
C:\Program Files\IrfanView\i_view64.exe
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$RootPath,

  [string]$IrfanExe = "C:\Program Files\IrfanView\i_view64.exe",

  [int]$TargetDpi = 96
)

# --- Preconditions ---
if (-not (Test-Path -LiteralPath $IrfanExe)) {
  throw "IrfanView not found at: $IrfanExe"
}

if (-not (Test-Path -LiteralPath $RootPath)) {
  throw "RootPath does not exist: $RootPath"
}

$RootPath = (Resolve-Path -LiteralPath $RootPath).Path

[int]$TotalScanned = 0
[int]$Updated = 0
[int]$Failed = 0

Write-Host "== JPEG DPI Normalizer =="
Write-Host "Root folder: $RootPath"
Write-Host "IrfanView: $IrfanExe"
Write-Host "Target DPI: $TargetDpi"
Write-Host "Dry-run mode: $($WhatIfPreference)"
Write-Host ""

Get-ChildItem -LiteralPath $RootPath -Recurse -File |
  Where-Object { $_.Extension -match '^\.(jpg|jpeg)$' } |
  ForEach-Object {

    $TotalScanned++
    $src = $_.FullName

    Write-Host "Processing: $src"

    if ($PSCmdlet.ShouldProcess($src, "Set DPI to $TargetDpi")) {
      & "$IrfanExe" `
        "$src" `
        "/jpgdpi=($TargetDpi,$TargetDpi)" `
        "/overwrite" `
        "/silent"

      if ($LASTEXITCODE -eq 0) {
        $Updated++
        Write-Host "  DPI set to $TargetDpi"
      }
      else {
        $Failed++
        Write-Warning "  Failed to update DPI"
      }
    }
    else {
      Write-Host "  [WhatIf] Would set DPI to $TargetDpi"
    }
  }

Write-Host ""
Write-Host "== Summary =="
Write-Host ("JPEGs scanned:  {0}" -f $TotalScanned)
Write-Host ("JPEGs updated:  {0}" -f $Updated)
Write-Host ("Failures:       {0}" -f $Failed)
Write-Host ""
Write-Host "Done."
