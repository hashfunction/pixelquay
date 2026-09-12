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
foreach($operation in @({Send-PixelQuayKeys @{} @{} @(17,79)}, {Send-PixelQuayText @{} @{} 'C:\owned\image.png'}, {Send-PixelQuayFileNameKeys @{} @{} 220 @(13)}, {Send-PixelQuayFileNameText @{} @{} 220 'C:\owned\image.png'})) {
    $errorText=$null
    try{& $operation}catch{$errorText=$_.Exception.Message}
    if($errorText -cne 'foreign target'){throw 'Input wrapper did not refuse before native input'}
    $count++
}
"PASS $count native ownership and pre-input refusal cases"
function New-ObservedFileName {
    [PixelQuayQualification.FileNameEvidence]@{Window=200;Focus=220;ExpectedFocus=220;Active=200;DialogPid=17;FocusPid=17;Exists=$true;Visible=$true;Enabled=$true;Descendant=$true;ReadOnly=$false;HasFileNameId=$true;Class='Edit'}
}
[PixelQuayQualification.ConsumerNative]::ValidateFileName((New-ObservedFileName))
$focusCases=1
foreach($change in @(@{Focus=0},@{ExpectedFocus=999},@{Active=999},@{FocusPid=99},@{Exists=$false},@{Visible=$false},@{Enabled=$false},@{Descendant=$false},@{ReadOnly=$true},@{HasFileNameId=$false},@{Class='SearchBox'})) {
    $e=New-ObservedFileName
    foreach($key in $change.Keys){$e.$key=$change[$key]}
    $failed=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateFileName($e)}catch{$failed=$true}
    if(-not $failed){throw "Accepted unsafe filename observation: $($change.Keys -join ',')"};$focusCases++
}
$guiType=[PixelQuayQualification.ConsumerNative].GetNestedType('GUIINFO',[Reflection.BindingFlags]::NonPublic)
if([IntPtr]::Size -eq 8 -and [Runtime.InteropServices.Marshal]::SizeOf([Activator]::CreateInstance($guiType)) -ne 72){throw 'GUITHREADINFO differs from Windows x64 ABI'}
"PASS $focusCases focused native filename ownership cases and GUI ABI"
# The production final native send boundary must observe focus after its last
# target check. Reproduce a child-focus change in that exact interval.
$script:boundaryEvents=[Collections.Generic.List[string]]::new()
$script:boundaryFocus=220
$targetCheck=[Action]{ $script:boundaryEvents.Add('target');$script:boundaryFocus=999 }
$focusCheck=[Action]{
    $script:boundaryEvents.Add('focus')
    $e=New-ObservedFileName;$e.Focus=$script:boundaryFocus
    [PixelQuayQualification.ConsumerNative]::ValidateFileName($e)
}
$deliver=[Func[uint32]]{ $script:boundaryEvents.Add('send');return 2 }
$failed=$false
try{[PixelQuayQualification.ConsumerNative]::DeliverInput($targetCheck,$focusCheck,$deliver,2)}catch{$failed=$true}
if(-not $failed -or ($script:boundaryEvents -join ',') -cne 'target,focus'){throw 'Changed filename focus reached final native input'}
$script:boundaryEvents.Clear();$script:boundaryFocus=220
$targetCheck=[Action]{ $script:boundaryEvents.Add('target') }
[PixelQuayQualification.ConsumerNative]::DeliverInput($targetCheck,$focusCheck,$deliver,2)
if(($script:boundaryEvents -join ',') -cne 'target,focus,send'){throw 'Final filename boundary order changed'}
$script:boundaryEvents.Clear()
[PixelQuayQualification.ConsumerNative]::DeliverInput($targetCheck,$null,$deliver,2)
if(($script:boundaryEvents -join ',') -cne 'target,send'){throw 'Generic input gained filename requirements'}
foreach($accepted in @(0,1)) {
    $script:boundaryEvents.Clear();$script:accepted=$accepted
    $partial=[Func[uint32]]{ $script:boundaryEvents.Add('send');return $script:accepted }
    $failed=$false;try{[PixelQuayQualification.ConsumerNative]::DeliverInput($targetCheck,$focusCheck,$partial,2)}catch{$failed=$true}
    if(-not $failed -or ($script:boundaryEvents -join ',') -cne 'target,focus,send'){throw 'Partial or failed native send did not fail immediately'}
}
$failed=$false;try{[PixelQuayQualification.ConsumerNative]::FileNameReadOnly(0)}catch{$failed=$true}
if(-not $failed){throw 'Unavailable style was treated as writable'}
if([PixelQuayQualification.ConsumerNative]::FileNameReadOnly(0x50000000)){throw 'Writable child Edit was rejected'}
if(-not [PixelQuayQualification.ConsumerNative]::FileNameReadOnly(0x50000800)){throw 'Read-only child Edit was accepted'}
'PASS5 production native delivery boundary cases and3 style-read cases'
$script:boundaryEvents.Clear()
$targetFailure=[Action]{ $script:boundaryEvents.Add('target');throw 'Target ownership lost' }
$failed=$false;try{[PixelQuayQualification.ConsumerNative]::DeliverInput($targetFailure,$focusCheck,$deliver,2)}catch{$failed=$true}
if(-not $failed -or ($script:boundaryEvents -join ',') -cne 'target'){throw 'Target failure reached filename or input boundary'}
foreach($operation in @(
    {[PixelQuayQualification.ConsumerNative]::FileNameChord($null,0,$null,0,'',0,@(13))},
    {[PixelQuayQualification.ConsumerNative]::FileNameTextInput($null,0,$null,0,'',0,'path')}
)) {
    $message=$null;try{& $operation}catch{$message=$_.Exception.Message}
    if($message -notlike '*Retained filename focus required*'){throw 'Filename API reached native calls without retained focus'}
}
'PASS target refusal and2 production filename APIs rejecting absent retained focus'
