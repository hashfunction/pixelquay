# Copyright 2026 Trieflow LLC. MIT. Normal native UI only; large authored user content.
# The qualified helper files remain unchanged. Only this separate screenshot
# driver supplies the native filename control directly, with the same ownership
# and complete text readback checks. Normal Open/Save/Choose still execute in-app.
function Set-TintNativeFilename([long]$Window,[string]$Text) {
    if(-not ('TintFableMarketing.Filename' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'capture_filename.cs')}
    [TintFableMarketing.Filename]::Set($Window,$Text)
}
function Send-PixelQuayFileNameText($Ui,$Scope,[long]$Focus,[string]$Text) {
    if($Text.Length -lt 1 -or $Text.Length -gt 4096 -or $Text.Contains([char]0)){throw 'Unbounded capture filename text'}
    if($Ui.record.Contains('capture_filename_writes') -and $Ui.record.capture_filename_writes.Count -ge 8){throw 'Capture filename write bound exceeded'}
    Assert-PixelQuayScope $Ui $Scope
    $null=[PixelQuayQualification.ConsumerNative]::FileName($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus)
    Set-TintNativeFilename $Focus $Text
    Assert-PixelQuayScope $Ui $Scope
    $null=[PixelQuayQualification.ConsumerNative]::FileName($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus)
    $actual=[PixelQuayQualification.ConsumerNative]::FileNameText($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus)
    if($actual -cne $Text){throw 'Native capture filename write did not retain exact text'}
    if(-not $Ui.record.Contains('capture_filename_writes')){$Ui.record.capture_filename_writes=[Collections.Generic.List[object]]::new()}
    $Ui.record.capture_filename_writes.Add(@{title=$Scope.title;hwnd=$Scope.hwnd;focus=$Focus;expected=$Text;actual=$actual;delivery='WM_SETTEXT';timeout_ms=1000})
}
function Send-PixelQuayKeys($Ui,$Scope,[int[]]$Keys) {
    Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::Chord($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Keys)
    # Allow the normal mnemonic's queued focus transition to finish before the
    # original exact Edit observation. No ownership error or input is retried.
    Start-Sleep -Milliseconds 1000
}
function Invoke-TintCaptureFiles([string]$Operation,[string]$StatePath,[string[]]$Extra=@()) {
    $result=& python (Join-Path $PSScriptRoot 'capture_files.py') $Operation --state $StatePath @Extra
    if($LASTEXITCODE -ne 0){throw "Independent capture file check failed: $Operation"}
    ($result -join "`n")|ConvertFrom-Json -AsHashtable
}
function Invoke-TintCaptureUi($Ui,[string]$StatePath) {
    $fixture=Get-Content -LiteralPath $StatePath -Raw|ConvertFrom-Json -AsHashtable
    $main=Get-PixelQuayMain $Ui 'Unsaved Image 1 - TintFable'
    Set-TintMaximizedPlacement $Ui $main
    $main=Open-PixelQuayImage $Ui $main.title (Join-Path $fixture.root 'Cedar Coast - draft.png') 'Cedar Coast - draft.png - TintFable'
    Send-PixelQuayKeys $Ui $main @(17,72)
    $main=Save-PixelQuayImage $Ui 'Cedar Coast - draft.png* - TintFable' (Join-Path $fixture.root 'Cedar Coast.png') 'Cedar Coast.png - TintFable'
    $Ui.record.edited=Invoke-TintCaptureFiles edited $StatePath
    # Original ViewActions.cs binds Best Fit to Ctrl+B. Ordinary UI keeps the
    # large artwork fully visible without changing any document pixels.
    Send-PixelQuayKeys $Ui $main @(17,66)
    Save-TintCaptureFrame $Ui $main '01-edited-canvas' 'Cedar Coast.png - TintFable'
    Send-PixelQuayKeys $Ui $main @(17,18,69)
    $recipe=Wait-PixelQuayConsumer {Get-PixelQuayScope $Ui 'Export with Recipe'} 'real export recipe dialog'
    Set-PixelQuayRecipeField $Ui $recipe 78 'Newsletter banner'
    Set-PixelQuayRecipeField $Ui $recipe 87 '1200'
    Set-PixelQuayRecipeField $Ui $recipe 72 '800'
    Set-PixelQuayRecipeField $Ui $recipe 83 '-newsletter'
    Send-PixelQuayKeys $Ui $recipe @(9);Send-PixelQuayKeys $Ui $recipe @(9);Send-PixelQuayKeys $Ui $recipe @(32)
    Send-PixelQuayKeys $Ui $recipe @(27)
    $main=Get-PixelQuayMain $Ui 'Cedar Coast.png - TintFable'
    Send-PixelQuayKeys $Ui $main @(17,18,69)
    $recipe=Wait-PixelQuayConsumer {Get-PixelQuayScope $Ui 'Export with Recipe'} 'saved newsletter recipe reopened'
    Send-PixelQuayKeys $Ui $recipe @(18,83)
    foreach($i in 1..3){Send-PixelQuayKeys $Ui $recipe @(9)}
    Send-PixelQuayKeys $Ui $recipe @(32)
    Set-PixelQuayPickerPath $Ui 'Export destination' $fixture.root
    $recipe=Wait-PixelQuayConsumer {Get-PixelQuayScope $Ui 'Export with Recipe'} 'real export folder accepted'
    Save-TintCaptureFrame $Ui $recipe '02-export-recipe' 'Cedar Coast.png - TintFable'
    Send-PixelQuayKeys $Ui $recipe @(18,69)
    Wait-PixelQuayConsumer {Test-Path -LiteralPath (Join-Path $fixture.root 'Cedar Coast-newsletter.png') -PathType Leaf} 'actual exported newsletter PNG'|Out-Null
    $Ui.record.exported=Invoke-TintCaptureFiles exported $StatePath
    $completion=Wait-PixelQuayConsumer {Get-PixelQuayScope $Ui '' -Completion} 'owned native export completion'
    Send-PixelQuayKeys $Ui $completion @(13)
    $main=Open-PixelQuayImage $Ui 'Cedar Coast.png - TintFable' (Join-Path $fixture.root 'Cedar Coast-newsletter.png') 'Cedar Coast-newsletter.png - TintFable'
    Send-PixelQuayKeys $Ui $main @(17,66)
    Save-TintCaptureFrame $Ui $main '03-exported-image' 'Cedar Coast-newsletter.png - TintFable'
    # A second ordinary rotate/save proves the native editor actually reopened
    # the exported bytes. The three original screenshots remain untouched.
    Send-PixelQuayKeys $Ui $main @(17,72)
    $main=Save-PixelQuayImage $Ui 'Cedar Coast-newsletter.png* - TintFable' (Join-Path $fixture.root 'Cedar Coast - reopened.png') 'Cedar Coast - reopened.png - TintFable'
    $Ui.record.reopened=Invoke-TintCaptureFiles reopened $StatePath
    $Ui.record.ui_actions_completed=$true
}
