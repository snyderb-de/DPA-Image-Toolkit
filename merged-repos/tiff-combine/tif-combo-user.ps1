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
Get-ChildItem -Path $path -Filter '*.tiff' | Rename-Item -NewName { $_.Name -replace '\.tiff$', '.tif' }

# Create "combined-tifs" subfolder
$combinedTifsFolder = Join-Path -Path $path -ChildPath "combined-tifs"
if (-not (Test-Path -Path $combinedTifsFolder)) {
    New-Item -Path $combinedTifsFolder -ItemType Directory | Out-Null
}

# Define a function to use IrfanView to combine TIFFs
function Merge-Images {
    param(
        [string]$Group,
        [string]$InputDirectory,
        [string]$OutputDirectory,
        [System.Windows.Forms.TextBox]$LogTextBox,
        [System.Windows.Forms.ProgressBar]$ProgressBar
    )
    # Get the TIFF files that belong to the group
    $files = Get-ChildItem -Path $InputDirectory -Filter "$Group*.tif"
    $inputFiles = $files | ForEach-Object -Process { $_.FullName }
    $inputFilesJoined = $inputFiles -join ','

    foreach ($file in $inputFiles) {
        $LogTextBox.Invoke({ 
            $LogTextBox.AppendText("Processing file: $($file)`r`n")
            $LogTextBox.SelectionStart = $LogTextBox.TextLength
            $LogTextBox.ScrollToCaret()
        })
        # Start-Sleep -Seconds 1 # slowing the progress bar a bit
        $ProgressBar.Invoke({ $ProgressBar.Value++ })
    }

    # Merge the TIFF files
    $outputFile = Join-Path -Path $OutputDirectory -ChildPath "$Group.tif"
    & "$env:ProgramFiles\IrfanView\i_view64.exe" /cmdexit "/multitif=($outputFile,$inputFilesJoined)" 

    # Return the files that were merged
    return $files
}

# Function to extract group name based on conventions
function Get-GroupName {
    param(
        [string]$FileName
    )

    # Determine the group based on the number of underscores
    $underscoreCount = ([regex]::Matches($FileName, "_")).Count
    switch ($underscoreCount) {
        1 { $FileName -replace "_.*" }
        2 { 
            # Adjusting regex to correctly capture the group name between two underscores
            if ($FileName -match "^(.*?_.*)_\d+\..*$") { 
                $matches[1] 
            }
        }
        default { $FileName }
    }
}

# Get the TIFF files that match the specific pattern
$files = Get-ChildItem -Path $path -Filter '*.tif*' | Where-Object { $_.Name -match '.*_\d+.*' }

# Group the files based on the new logic
$groups = $files | Group-Object { Get-GroupName $_.Name }

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

# Convert the grouped files into a table format string
# Limit the output to the first 3 groups for the summary message
$limitedGroupedFiles = $groupedFiles | Select-Object -First 3
$summaryTableString = "Showing the first 3 Groups as an example...`nGroup`nFiles to combine`n"
$limitedGroupedFiles | ForEach-Object {
$summaryTableString += "`n" + (Format-GroupString -Group $_)
}

# If there are more than 3 groups, add an additional line to the table for the summary
if ($groupedFiles.Count -gt 3) {
    $summaryTableString += "`n... and $($groupedFiles.Count - 3) more groups."
}

# Combine the summary, table, and question into one string for the summary
$message = @"
Pre-Combine Summary:
Total groups: $totalGroups
Total files: $totalFiles

$summaryTableString

Do you wish to continue with the operation?
"@

# Display the entire message in one dialog box
$userInput = [System.Windows.Forms.MessageBox]::Show($message, "Confirmation", [System.Windows.Forms.MessageBoxButtons]::YesNo)

# Create a function to handle the processing
function Invoke-GroupProcessing {
    param(
        [System.Collections.ObjectModel.Collection[System.Management.Automation.PSObject]]$Groups,
        [string]$InputDirectory,
        [string]$OutputDirectory,
        [System.Windows.Forms.TextBox]$LogTextBox,
        [System.Windows.Forms.ProgressBar]$ProgressBar,
        [System.Windows.Forms.Button]$OkButton
    )

    $mergedFiles = @()
    $totalFiles = ($Groups | ForEach-Object { ($_.Group).Count } | Measure-Object -Sum).Sum
    $ProgressBar.BeginInvoke({ $ProgressBar.Maximum = $totalFiles })

    foreach ($group in $Groups) {
        $LogTextBox.Invoke({
            $LogTextBox.AppendText("Processing group: $($group.Name)`r`n")
            $LogTextBox.SelectionStart = $LogTextBox.TextLength
            $LogTextBox.ScrollToCaret()
        })
    
        # Call Merge-Images function here
        $merged = Merge-Images -Group $group.Name -InputDirectory $InputDirectory -OutputDirectory $OutputDirectory -LogTextBox $LogTextBox -ProgressBar $ProgressBar
        $mergedFiles += New-Object PSObject -Property @{
            'GroupName' = $group.Name
            'MergedFile' = Join-Path -Path $OutputDirectory -ChildPath "$($group.Name).tif"
            'FileCount' = $merged.Count
        }
    
        $LogTextBox.Invoke({
            $LogTextBox.AppendText("Finished processing group: $($group.Name)`r`n`r`n")
            $LogTextBox.SelectionStart = $LogTextBox.TextLength
            $LogTextBox.ScrollToCaret()
        })
        # Start-Sleep -Seconds 1
    }

    $LogTextBox.BeginInvoke({
        $LogTextBox.AppendText("Job complete.`r`n")
        $LogTextBox.SelectionStart = $LogTextBox.TextLength
        $LogTextBox.ScrollToCaret()
    })
    $OkButton.BeginInvoke({ $OkButton.Enabled = $true })

    $mergedFiles
}



# If the user enters 'Yes', then proceed. Otherwise, exit the script.
if ($userInput -eq 'Yes') {
    # Create a custom dialog with a log TextBox, a ProgressBar, and a DataGridView
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Processing Your Files Into Groups"
    $form.Width = 600
    $form.Height = 400

    $logTextBox = New-Object System.Windows.Forms.TextBox
    $logTextBox.Multiline = $true
    $logTextBox.ReadOnly = $true
    $logTextBox.Dock = [System.Windows.Forms.DockStyle]::Fill
    $logTextBox.ScrollBars = 'Vertical'
    $form.Controls.Add($logTextBox)

    $progressBar = New-Object System.Windows.Forms.ProgressBar
    $progressBar.Height = 20
    $progressBar.Dock = [System.Windows.Forms.DockStyle]::Bottom
    $form.Controls.Add($progressBar)

    $okButton = New-Object System.Windows.Forms.Button
    $okButton.Text = "OK"
    $okButton.Enabled = $false
    $okButton.Add_Click({ $form.Close() })
    $okButton.Dock = [System.Windows.Forms.DockStyle]::Bottom
    $form.Controls.Add($okButton)

# Hook up a Load event to call the Invoke-GroupProcessing function when the form loads
$form.Add_Load({
    $script:mergedFiles = Invoke-GroupProcessing -Groups $groups -InputDirectory $path -OutputDirectory $combinedTifsFolder -LogTextBox $logTextBox -ProgressBar $progressBar -OkButton $okButton
})

# Show the dialog as a modal dialog
$form.ShowDialog() | Out-Null

} else {
    [System.Windows.Forms.MessageBox]::Show("Operation cancelled by user.") | Out-Null
    exit
}