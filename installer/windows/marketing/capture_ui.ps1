# Copyright 2026 Trieflow LLC. MIT. Normal native UI only; large authored user content.
function Invoke-TintPacedFileNameText([string]$Text,[scriptblock]$Send) {
    if($Text.Length -lt 1 -or $Text.Length -gt 4096 -or $Text.Contains([char]0)){throw 'Unbounded capture filename text'}
    foreach($character in $Text.ToCharArray()){& $Send ([string]$character)}
}
# Capture-only input pacing: every distinct UTF-16 character goes through the
# original native owner/focus gate once, including its 100 ms dispatch interval.
# Keep the qualified source and its full-path readback/acceptance untouched.
function Send-PixelQuayFileNameText($Ui,$Scope,[long]$Focus,[string]$Text) {
    Invoke-TintPacedFileNameText $Text {
        param($character)
        Assert-PixelQuayScope $Ui $Scope
        [PixelQuayQualification.ConsumerNative]::FileNameTextInput($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus,$character)
    }
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
