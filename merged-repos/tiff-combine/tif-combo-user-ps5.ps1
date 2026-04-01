Add-Type -AssemblyName System.Windows.Forms

# User should choose folder of TIFFs
$folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
$folderBrowser.Description = "Please select the folder containing your TIFF files"
$folderBrowser.ShowDialog() | Out-Null
$path = $folderBrowser.SelectedPath

function Format-GroupString {
    param (
        [PSCustomObject]$Group
    )
    return "{0,-30}`n{1}`n`n" -f $Group.Group, $Group.Files
}

if (!(Test-Path $path) -or !(Test-Path $path -PathType Container)) {
    [System.Windows.Forms.MessageBox]::Show("The path you entered does not exist or is not a directory.")
    exit
}

# Rename .tiff files to .tif
Get-ChildItem -Path $path -Filter '*.tiff' | Rename-Item -NewName { $_.Name -replace '\\.tiff$', '.tif' }

# After renaming .tiff to .tif
Write-Host "Renamed files:"
Get-ChildItem -Path $path -Filter '*.tif' | ForEach-Object { Write-Host $_.FullName }


# Create "combined-tifs" subfolder
$combinedTifsFolder = Join-Path -Path $path -ChildPath "combined-tifs"
if (-not (Test-Path -Path $combinedTifsFolder)) {
    New-Item -Path $combinedTifsFolder -ItemType Directory | Out-Null
}

function Merge-Images {
    param (
        [string]$Group,
        [string]$InputDirectory,
        [string]$OutputDirectory
    )

    # Get the TIFF files that belong to the group
    $files = Get-ChildItem -Path $InputDirectory -Filter "$Group*.tif"
    $inputFiles = $files | ForEach-Object -Process { $_.FullName }
    $inputFilesJoined = $inputFiles -join ','

    # Merge the TIFF files
    $outputFile = Join-Path -Path $OutputDirectory -ChildPath "$Group.tif"
    & "$env:ProgramFiles\\IrfanView\\i_view64.exe" /cmdexit "/multitif=($outputFile,$inputFilesJoined)" 

    # Return the files that were merged
    return $files
}

function Get-GroupName {
    param (
        [string]$FileName
    )

    # Determine the group based on the number of underscores
    $underscoreCount = ([regex]::Matches($FileName, "_")).Count
    switch ($underscoreCount) {
        1 { $FileName -replace "_.*" }
        2 { 
            if ($FileName -match "^(.*?_.*)_\\d+\\..*$") { 
                $matches[1] 
            }
        }
        default { $FileName }
    }
}

$files = Get-ChildItem -Path $path -Filter '*.tif' | Where-Object { $_.Name -match '.*\\d+.*' }

$groups = $files | Group-Object { Get-GroupName $_.Name }

$groupedFiles = foreach ($group in $groups) {
    [PSCustomObject]@{
        Group = $group.Name
        Files = ($group.Group | ForEach-Object { $_.Name }) -join ', '
    }
}

# After grouping
Write-Host "Groups found:"
$groups | ForEach-Object { Write-Host $_.Name }


$totalGroups = $groupedFiles.Count
$totalFiles = $files.Count

$limitedGroupedFiles = $groupedFiles | Select-Object -First 3
$summaryTableString = "Showing the first 3 Groups as an example...`nGroup`nFiles to combine`n"
$limitedGroupedFiles | ForEach-Object { $summaryTableString += "`n" + (Format-GroupString -Group $_) }

if ($groupedFiles.Count -gt 3) {
    $summaryTableString += "`n... and $($groupedFiles.Count - 3) more groups."
}

$message = @"
Pre-Combine Summary:
Total groups: $totalGroups
Total files: $totalFiles

$summaryTableString

Do you wish to continue with the operation?
"@
$userInput = [System.Windows.Forms.MessageBox]::Show($message, "Confirmation", [System.Windows.Forms.MessageBoxButtons]::YesNo)

if ($userInput -eq 'Yes') {
    # Processing each group
    foreach ($group in $groups) {
        Write-Host "Processing group: $($group.Name)"
        Merge-Images -Group $group.Name -InputDirectory $path -OutputDirectory $combinedTifsFolder
        Write-Host "Finished processing group: $($group.Name)"
    }
    Write-Host "Job complete. All TIFF files have been successfully merged in the 'combined-tifs' folder."
} else {
    Write-Host "Operation cancelled by the user."
}