# User should choose folder of tifs
$path = Read-Host "Please input the path to your TIFF files"
if (!(Test-Path $path) -or !(Test-Path $path -PathType Container)) {
    Write-Host "The path you entered does not exist or is not a directory."
    exit
}

# Define a function to use IrfanView to combine TIFFs
function Merge-Images {
    param(
        [string]$Group,
        [string]$InputDirectory,
        [string]$OutputDirectory
    )
    # Get the TIFF files that belong to the group
    $files = Get-ChildItem -Path $InputDirectory -Filter "$Group*.tif"
    $inputFiles = $files | ForEach-Object -Process { $_.FullName }
    $inputFilesJoined = $inputFiles -join ','

    # Merge the TIFF files
    & "$env:ProgramFiles\IrfanView\i_view64.exe" /cmdexit "/multitif=($OutputDirectory\$Group.tif,$inputFilesJoined)" 

    # Return the files that were merged
    return $files
}

# Get the TIFF files
$files = Get-ChildItem -Path $path -Filter '*.tif'

# Group the files by the sequence number
$groups = $files | Group-Object {$_.BaseName -replace '_\d{3}$'}

# For each group, create a custom object with the group name and the files in the group
$groupedFiles = foreach ($group in $groups) {
    [PSCustomObject]@{
        Group  = $group.Name
        Files = ($group.Group | ForEach-Object { $_.Name }) -join ', '
    }
}

# Show the totals for Groups and Files
$totalGroups = $groupedFiles.Count
$totalFiles = $files.Count
Write-Host "`nPre-Combine Summary:"
Write-Host "Total groups: $totalGroups"
Write-Host "Total files: $totalFiles"

# Output the grouped files in a table format
$groupedFiles | Format-Table -AutoSize

# Then ask the user if they want to continue
$userInput = Read-Host "`nDo you wish to continue with the operation? (Y/N)"

# If the user enters 'Y' or 'y', then proceed. Otherwise, exit the script.
if ($userInput -eq 'Y' -or $userInput -eq 'y') {
    Write-Host "Continuing with the operation..."
    $mergedFiles = @()
    foreach ($group in $groups) {
        Write-Host "Processing group $($group.Name)..."
        $merged = Merge-Images -Group $group.Name -InputDirectory $path -OutputDirectory $path
        $mergedFiles += New-Object PSObject -Property @{
            'GroupName' = $group.Name
            'MergedFile' = "$path\$($group.Name).tif"
            'FileCount' = $merged.Count
        }
        Write-Host "Finished processing group $($group.Name)"
    }

    Write-Host "Operation completed successfully. Here are the merged files:"
    $mergedFiles | Format-Table

    $userInput = Read-Host "`nDo you wish to clean up the input files? (Y/N)"
    if ($userInput -eq 'Y' -or $userInput -eq 'y') {
        Write-Host "Cleaning up input files..."
        foreach ($group in $mergedFiles) {
            Get-ChildItem -Path "$path\$($group.GroupName)_*.tif" | Remove-Item -Confirm:$false
        }
        Write-Host "Clean up completed successfully."
    }
}
else {
    Write-Host "Operation cancelled by user."
    exit
}
