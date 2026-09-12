# Copyright 2026 Trieflow LLC. MIT. Production native UI sequence; side effects recorded.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_ui.ps1')
$stream=[Collections.Generic.List[string]]::new()
Invoke-TintPacedFileNameText 'C:\TintFable Demo\Cedar Coast.png' {param($character)$stream.Add($character)}
if(($stream -join '') -cne 'C:\TintFable Demo\Cedar Coast.png' -or @($stream|Where-Object Length -NE 1).Count){throw 'Paced filename input duplicated or batched characters'}
$stream.Clear();$failed=$false
try{Invoke-TintPacedFileNameText 'abcdef' {param($character)if($character -ceq 'c'){throw 'original ownership refusal'};$stream.Add($character)}}catch{if($_.Exception.Message -cne 'original ownership refusal'){throw};$failed=$true}
if(-not $failed -or ($stream -join '') -cne 'ab'){throw 'Paced input continued or replayed after native refusal'}
foreach($invalid in @('',('x'*4097),('a'+[char]0+'b'))){$stream.Clear();$failed=$false;try{Invoke-TintPacedFileNameText $invalid {param($character)$stream.Add($character)}}catch{$failed=$true};if(-not $failed -or $stream.Count){throw 'Invalid filename delivered input'}}
Write-Output 'PASS exact one-shot character stream, unchanged refusal propagation and pre-input text bounds.'
$script:events=[Collections.Generic.List[string]]::new();$script:refusal='none';$script:mainTitle='Unsaved Image 1 - TintFable'
function Event([string]$Value){$script:events.Add($Value);if($Value -ceq $script:refusal){throw 'Original UI/file refusal'}}
function Get-PixelQuayMain($Ui,$Title){Event ('main:'+ $Title);if($Title -cne $script:mainTitle){throw 'Unknown main title assumption'};return @{title=$Title}}
function Set-TintMaximizedPlacement($Ui,$Scope){Event 'placement'}
function Open-PixelQuayImage($Ui,$Current,$Path,$Expected){if($Current -cne $script:mainTitle){throw 'Open from unknown document'};Event ('open:'+ [IO.Path]::GetFileName($Path));$script:mainTitle=$Expected;return @{title=$Expected}}
function Save-PixelQuayImage($Ui,$Current,$Path,$Expected){if($Current -cne $script:mainTitle){throw 'Save from unknown document'};Event ('save:'+ [IO.Path]::GetFileName($Path));$script:mainTitle=$Expected;return @{title=$Expected}}
function Send-PixelQuayKeys($Ui,$Scope,$Keys){Event ('keys:'+($Keys -join ','));if(($Keys -join ',') -ceq '17,72'){$script:mainTitle=$script:mainTitle.Replace(' - TintFable','* - TintFable')}}
function Set-PixelQuayRecipeField($Ui,$Scope,$Mnemonic,$Text){Event ('field:'+ $Mnemonic+':'+$Text)}
function Get-PixelQuayScope($Ui,$Title,[switch]$Completion){Event ('scope:'+ $Title);return @{title=$Title}}
function Wait-PixelQuayConsumer($Observe,$Label){Event ('wait:'+ $Label);return & $Observe}
function Set-PixelQuayPickerPath($Ui,$Title,$Path){Event ('picker:'+ $Title)}
function Save-TintCaptureFrame($Ui,$Scope,$Stem,$MainTitle){if($MainTitle -cne $script:mainTitle){throw 'Wrong main image beneath screenshot'};Event ('frame:'+ $Stem)}
function Invoke-TintCaptureFiles($Operation,$StatePath){Event ('oracle:'+ $Operation);return @{actualFixture=$true}}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('tint-ui-sequence-'+[guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($temp)|Out-Null
try{
    $state=Join-Path $temp 'state.json';@{root=$temp}|ConvertTo-Json|Set-Content $state
    [IO.File]::WriteAllText((Join-Path $temp 'Cedar Coast-newsletter.png'),'explicit UI sequence fixture; file oracle tested separately')
    foreach($failure in @('none','oracle:edited','frame:02-export-recipe','oracle:exported','oracle:reopened')){
        $script:events.Clear();$script:refusal=$failure;$script:mainTitle='Unsaved Image 1 - TintFable';$ui=@{record=@{}};$failed=$false
        try{Invoke-TintCaptureUi $ui $state}catch{if($_.Exception.Message -cne 'Original UI/file refusal'){throw};$failed=$true}
        if(($failure -ceq 'none') -eq $failed){throw 'UI failure not propagated'}
        if($failed){if($ui.record.ContainsKey('ui_actions_completed') -or $script:events[$script:events.Count-1] -cne $failure){throw 'Input continued after original refusal'};continue}
        $frames=@($script:events|Where-Object {$_ -like 'frame:*'})
        if(($frames -join '|') -cne 'frame:01-edited-canvas|frame:02-export-recipe|frame:03-exported-image'){throw 'Requested image slots or order changed'}
        foreach($pair in @(@('oracle:edited','frame:01-edited-canvas'),@('picker:Export destination','frame:02-export-recipe'),@('oracle:exported','frame:03-exported-image'))){if($script:events.IndexOf($pair[0]) -ge $script:events.IndexOf($pair[1])){throw 'Screenshot preceded corresponding actual output proof'}}
        if(@($script:events|Where-Object {$_ -ceq 'keys:17,66'}).Count -ne 2 -or -not $ui.record.ui_actions_completed){throw 'Actual best-fit UI or final reopened proof missing'}
        foreach($field in @('field:78:Newsletter banner','field:87:1200','field:72:800','field:83:-newsletter')){if($field -cnotin $script:events){throw 'Real recipe input changed'}}
    }
}finally{Remove-Item $temp -Recurse -Force}
Write-Output 'PASS real capture UI sequence, Best Fit, recipe persistence/reopen and four input/file refusal boundaries.'
