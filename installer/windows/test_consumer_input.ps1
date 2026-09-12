# Exercise the same managed ownership predicate used immediately before SendInput.
# Copyright 2026 Trieflow LLC. MIT licensed.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'consumer_native.cs')
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
function New-ObservedTarget {
    [PixelQuayQualification.ConsumerTargetEvidence]@{
        AppLive=$true;TargetLive=$true;MainLive=$true;WindowLive=$true;Visible=$true;Enabled=$true
        AppPid=17;MainPid=17;TargetPid=23;WindowPid=23;Main=100;Window=200;Foreground=200
        Owners=@(200,150,100);ExpectedTitle='Open Image File';Title='Open Image File'
    }
}
[PixelQuayQualification.ConsumerNative]::Validate((New-ObservedTarget),$true)
$inputType=[PixelQuayQualification.ConsumerNative].GetNestedType('INPUT',[Reflection.BindingFlags]::NonPublic)
if([IntPtr]::Size -eq 8 -and [Runtime.InteropServices.Marshal]::SizeOf([Activator]::CreateInstance($inputType)) -ne 40){throw 'Native INPUT layout differs from Windows x64 ABI'}
$count=2
foreach($change in @(
    @{AppLive=$false},@{TargetLive=$false},@{MainLive=$false},@{WindowLive=$false},@{Visible=$false},@{Enabled=$false},
    @{MainPid=99},@{WindowPid=99},@{Main=0},@{Window=0},@{Owners=@(200,150)},@{Title='Foreign dialog'},@{Foreground=999}
)) {
    $e=New-ObservedTarget
    foreach($key in $change.Keys){$e.$key=$change[$key]}
    $failed=$false
    try { [PixelQuayQualification.ConsumerNative]::Validate($e,$true) } catch { $failed=$true }
    if(-not $failed){throw "Unsafe native observation was accepted: $($change.Keys -join ',')"}
    $count++
}
# Actual UI wrapper must fail before native key/text code when scope validation refuses.
function Assert-PixelQuayScope { throw 'foreign target' }
foreach($operation in @({Send-PixelQuayKeys @{} @{} @(17,79)}, {Send-PixelQuayText @{} @{} 'C:\owned\image.png'})) {
    $errorText=$null
    try{& $operation}catch{$errorText=$_.Exception.Message}
    if($errorText -cne 'foreign target'){throw 'Input wrapper did not refuse before native input'}
    $count++
}
"PASS $count native ownership and pre-input refusal cases"
