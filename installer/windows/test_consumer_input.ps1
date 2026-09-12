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
foreach($operation in @({Send-PixelQuayKeys @{} @{} @(17,79)}, {Send-PixelQuayText @{} @{} 'C:\owned\image.png'}, {Send-PixelQuayFileNameKeys @{} @{} 220 @(13)}, {Send-PixelQuayFileNameText @{} @{} 220 'C:\owned\image.png'}, {Send-PixelQuayChooseSpace @{} @{} 220 'C:\owned' $null})) {
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
foreach($change in @(@{Window=0},@{DialogPid=0},@{Focus=0},@{ExpectedFocus=999},@{Active=999},@{FocusPid=99},@{Exists=$false},@{Visible=$false},@{Enabled=$false},@{Descendant=$false},@{ReadOnly=$true},@{HasFileNameId=$false},@{Class='SearchBox'})) {
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

# Hypothetical native Choose metadata exercises the predicate; the real numeric
# control ID must be queried on Windows, then retained across Tab and Space.
function New-ChooseEvidence {
 [PixelQuayQualification.ChooseButtonEvidence]@{Window=200;Filename=220;Button=230;Parent=200;DialogItem=230;NextTab=230;
  Focus=230;Active=200;DialogPid=17;ButtonPid=17;ControlId=47;Class='Button';Label='Choose';
  DialogThread=31;ButtonThread=31;Exists=$true;Visible=$true;Enabled=$true;Descendant=$true;CandidateCount=1;Style=0x50010001}
}
$choose=New-ChooseEvidence
[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($choose,'Export destination',$true,$choose)
foreach($change in @(@{Window=0},@{Filename=0},@{Button=0},@{Parent=201},@{DialogItem=240},@{NextTab=240},@{Focus=220},@{Active=201},
 @{DialogPid=0},@{ButtonPid=3},@{ControlId=0},@{Class='Edit'},@{Label='Cancel'},@{DialogThread=0},@{ButtonThread=32},@{Exists=$false},@{Visible=$false},@{Enabled=$false},@{Descendant=$false},@{CandidateCount=2},@{Style=0},@{Style=0x50010003})){
 $bad=New-ChooseEvidence;foreach($key in $change.Keys){$bad.$key=$change[$key]}
 $rejected=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($bad,'Export destination',$true,$choose)}catch{$rejected=$true}
 if(-not $rejected){throw "Unsafe Choose evidence accepted: $($change.Keys)"}
}
$before=New-ChooseEvidence;$before.Focus=220
[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($before,'Export destination',$false,$null)
foreach($title in @('Save Image File','Open Image File','Export Destination')){
 $rejected=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($choose,$title,$true,$choose)}catch{$rejected=$true}
 if(-not $rejected){throw 'Choose route accepted unrelated title'}
}
$changed=New-ChooseEvidence;$changed.ControlId=48
$rejected=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($changed,'Export destination',$true,$choose)}catch{$rejected=$true}
if(-not $rejected){throw 'Changed retained button ID was accepted'}
foreach($kind in @('replaced-hwnd','changed-thread','missing-retained')) {
 $e=New-ChooseEvidence;$prior=$choose
 if($kind -ceq 'replaced-hwnd'){$e.Button=240;$e.DialogItem=240;$e.NextTab=240;$e.Focus=240}
 if($kind -ceq 'changed-thread'){$e.DialogThread=32;$e.ButtonThread=32}
 if($kind -ceq 'missing-retained'){$prior=$null}
 $rejected=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($e,'Export destination',$true,$prior)}catch{$rejected=$true}
 if(-not $rejected){throw 'Replacement/unretained Choose binding accepted'}
}
# Exercise the real final send seam: target succeeds, focus moves, no key packet.
$script:boundaryEvents.Clear();$script:chooseFocus=230
$chooseTarget=[Action]{$script:boundaryEvents.Add('target');$script:chooseFocus=220}
$chooseFocus=[Action]{$script:boundaryEvents.Add('choose');$e=New-ChooseEvidence;$e.Focus=$script:chooseFocus;[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($e,'Export destination',$true,$choose)}
$rejected=$false;try{[PixelQuayQualification.ConsumerNative]::DeliverInput($chooseTarget,$chooseFocus,$deliver,2)}catch{$rejected=$true}
if(-not $rejected -or ($script:boundaryEvents -join ',') -cne 'target,choose'){throw 'Moved Choose focus reached native Space'}
'PASS source-labelled Choose ownership, 29 refusal cases and actual final focus boundary; numeric ID is fixture-only'
# Failure evidence must survive the real C# -> PowerShell exception wrapper.
$failedName=New-ObservedFileName;$failedName.Active=201;$failedName.HasFileNameId=$false
$failure=$null
try{[PixelQuayQualification.ConsumerNative]::ValidateFileName($failedName)}catch{$failure=$_}
if($null -eq $failure){throw 'Invalid filename topology was accepted'}
$ui=@{record=@{}}
$scope=@{hwnd=200;title='Save Image File';process=@{Id=17}}
Save-PixelQuayFileNameFailure $ui $scope 0 'observe-after-alt-n' $failure.Exception
$serialized=$ui.record.picker_failures|ConvertTo-Json -Depth 12|ConvertFrom-Json
if($serialized.native.Active -ne 201 -or $serialized.native.Window -ne 200 -or
 ($serialized.native.FailedPredicates -join ',') -cne 'active_window,filename_id_1148' -or
 $serialized.stage -cne 'observe-after-alt-n' -or $serialized.title -cne 'Save Image File'){
 throw 'Exact failing native predicates were lost through exception serialization'
}
'PASS real filename refusal evidence survives C# exception wrapping and JSON serialization'
$bad=New-ChooseEvidence;$bad.Label='Cancel';$failure=$null
try{[PixelQuayQualification.ConsumerNative]::ValidateChooseButton($bad,'Export destination',$true,$choose)}catch{$failure=$_}
$ui=@{record=@{}};$scope=@{hwnd=200;title='Export destination';process=@{Id=17}}
Save-PixelQuayFileNameFailure $ui $scope 220 'observe-focused-choose' $failure.Exception
$saved=$ui.record|ConvertTo-Json -Depth 12|ConvertFrom-Json
if($saved.picker_failures[0].choose_native.ControlId -ne 47 -or $saved.picker_failures[0].choose_native.Label -cne 'Cancel' -or $saved.picker_failures[0].native -ne $null){throw 'Native button identity/refusal did not survive exception JSON'}
'PASS queried Choose failure evidence survives real exception wrapping and bounded JSON'

# Replay diagnostic payloads, not claimed Windows topology: a foreign/non-1148
# chain must stay rejected while its precise classes/IDs/style remain inspectable.
$e=New-ObservedFileName;$e.HasFileNameId=$false;$e.Style=0x50000000;$e.DialogThread=31;$e.FocusThread=31
$e.Ancestors=@(
 [PixelQuayQualification.FileNameAncestorEvidence]@{Window=220;Parent=210;ProcessId=17;ControlId=1001;Descendant=$true;Class='Edit'},
 [PixelQuayQualification.FileNameAncestorEvidence]@{Window=210;Parent=200;ProcessId=17;ControlId=1002;Descendant=$true;Class='ComboBox'}
)
$failure=$null;try{[PixelQuayQualification.ConsumerNative]::ValidateFileName($e)}catch{$failure=$_}
if($null -eq $failure){throw 'Diagnostic alternate control IDs broadened filename acceptance'}
$ui=@{record=@{}};Save-PixelQuayFileNameFailure $ui $scope 220 'observe-before-enter' $failure.Exception
$saved=$ui.record|ConvertTo-Json -Depth 12|ConvertFrom-Json
if($saved.picker_failures[0].native.Ancestors.Count -ne 2 -or $saved.picker_failures[0].native.Ancestors[0].ControlId -ne 1001 -or
 $saved.picker_failures[0].native.Style -ne 0x50000000 -or $saved.picker_failures[0].native.FocusThread -ne 31){throw 'Bounded native chain/style/thread diagnostics were lost'}
for($i=1;$i -lt 16;$i++){Save-PixelQuayFileNameFailure $ui $scope 220 'observe-before-enter' $failure.Exception}
$refused=$false;try{Save-PixelQuayFileNameFailure $ui $scope 220 'observe-before-enter' $failure.Exception}catch{$refused=$true}
if(-not $refused -or $ui.record.picker_failures.Count -ne 16){throw 'Filename evidence bound failed'}
'PASS diagnostic chain/style/thread serialization and 16-record bound; alternate filename IDs remain refused'

# Actual Save Image File topology from Windows run34681764386. Only this
# exact native filename chain may supplement the established classic1148 route.
function New-ModernSaveEvidence {
    $e=New-ObservedFileName;$e.AncestryReachedDialog=$true;$e.AncestryTruncated=$false
    $e.Ancestors=@(
      [PixelQuayQualification.FileNameAncestorEvidence]@{Window=220;Parent=221;ProcessId=17;ControlId=1001;Descendant=$true;Class='Edit'},
      [PixelQuayQualification.FileNameAncestorEvidence]@{Window=221;Parent=222;ProcessId=17;ControlId=0;Descendant=$true;Class='ComboBox'},
      [PixelQuayQualification.FileNameAncestorEvidence]@{Window=222;Parent=223;ProcessId=17;ControlId=0;Descendant=$true;Class='FloatNotifySink'},
      [PixelQuayQualification.FileNameAncestorEvidence]@{Window=223;Parent=224;ProcessId=17;ControlId=0;Descendant=$true;Class='DirectUIHWND'},
      [PixelQuayQualification.FileNameAncestorEvidence]@{Window=224;Parent=200;ProcessId=17;ControlId=0;Descendant=$true;Class='DUIViewWndClassName'}
    );return $e
}
if(-not [PixelQuayQualification.ConsumerNative]::IsObservedModernSaveFileName((New-ModernSaveEvidence),'Save Image File')){throw 'Observed real Save filename chain rejected'}
foreach($title in @('Open Image File','Save As','Foreign dialog')) {
 if([PixelQuayQualification.ConsumerNative]::IsObservedModernSaveFileName((New-ModernSaveEvidence),$title)){throw 'Save filename route accepted another dialog'}
}
foreach($change in @(
 {param($e) $e.Ancestors[0].ControlId=1002}, {param($e) $e.Ancestors[0].Window=999},
 {param($e) $e.Ancestors[0].Parent=999}, {param($e) $e.Ancestors[1].Class='SearchBox'},
 {param($e) $e.Ancestors[2].ProcessId=99}, {param($e) $e.Ancestors[3].Descendant=$false},
 {param($e) $e.Ancestors[4].Parent=999}, {param($e) $e.Ancestors[1].ControlId=1001},
 {param($e) $e.AncestryReachedDialog=$false}, {param($e) $e.AncestryTruncated=$true},
 {param($e) $e.Ancestors=$e.Ancestors[0..3]}, {param($e) $e.Ancestors[1]=$null}
)) {
 $e=New-ModernSaveEvidence;& $change $e
 if([PixelQuayQualification.ConsumerNative]::IsObservedModernSaveFileName($e,'Save Image File')){throw 'Mutated Save filename chain accepted'}
}
'PASS actual modern Save topology plus15 wrong-title/chain refusals; native rerun still required'

# Run34682286222: Gtk SelectFolder displays an exact direct-child Edit1152
# under Export destination. This must not authorize other edits or dialog titles.
function New-ExportFolderEvidence {
    $e=New-ObservedFileName;$e.HasFileNameId=$false;$e.DialogThread=3056;$e.FocusThread=3056
    $e.AncestryReachedDialog=$true;$e.AncestryTruncated=$false
    $e.Ancestors=@([PixelQuayQualification.FileNameAncestorEvidence]@{
        Window=220;Parent=200;ProcessId=17;ControlId=1152;Descendant=$true;Class='Edit'
    });return $e
}
$folder=New-ExportFolderEvidence
if(-not [PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($folder,'Export destination')){throw 'Observed real export folder field rejected'}
$folder.HasFileNameId=[PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($folder,'Export destination')
[PixelQuayQualification.ConsumerNative]::ValidateFileName($folder)
$folderTopologyCases=1
foreach($title in @('Save Image File','Open Image File','Foreign dialog')) {
    if([PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName((New-ExportFolderEvidence),$title)){throw 'Export folder field accepted another dialog'}
    $folderTopologyCases++
}
if([PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($null,'Export destination')){throw 'Null folder evidence accepted'}
$folderTopologyCases++
foreach($change in @(
    {param($e)$e.Ancestors=$null}, {param($e)$e.Ancestors=@()}, {param($e)$e.Ancestors=@($null)},
    {param($e)$e.Ancestors=@($e.Ancestors[0],$e.Ancestors[0])},
    {param($e)$e.AncestryReachedDialog=$false}, {param($e)$e.AncestryTruncated=$true},
    {param($e)$e.Window=0}, {param($e)$e.Focus=0}, {param($e)$e.DialogPid=0},
    {param($e)$e.Ancestors[0].Window=0}, {param($e)$e.Ancestors[0].Window=999},
    {param($e)$e.Focus=200;$e.Ancestors[0].Window=200},
    {param($e)$e.Ancestors[0].Parent=999}, {param($e)$e.Ancestors[0].ProcessId=99},
    {param($e)$e.Ancestors[0].Descendant=$false}, {param($e)$e.Ancestors[0].Class='SearchBox'},
    {param($e)$e.Ancestors[0].ControlId=1148}, {param($e)$e.Ancestors[0].ControlId=1001},
    {param($e)$e.DialogThread=0;$e.FocusThread=0}, {param($e)$e.FocusThread=3057}
)) {
    $e=New-ExportFolderEvidence;& $change $e
    if([PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($e,'Export destination')){throw 'Mutated export folder topology accepted'}
    $folderTopologyCases++
}
# The recognized topology cannot suppress any existing focused-input predicate.
$folderGuardCases=0
foreach($change in @(@{ExpectedFocus=999},@{Active=999},@{FocusPid=99},@{Exists=$false},@{Visible=$false},@{Enabled=$false},@{Descendant=$false},@{ReadOnly=$true},@{Class='SearchBox'})) {
    $e=New-ExportFolderEvidence
    foreach($key in $change.Keys){$e.$key=$change[$key]}
    $e.HasFileNameId=[PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($e,'Export destination')
    $rejected=$false;try{[PixelQuayQualification.ConsumerNative]::ValidateFileName($e)}catch{$rejected=$true}
    if(-not $rejected){throw 'Recognized folder topology bypassed final filename validation'}
    $folderGuardCases++
}
$script:boundaryEvents.Clear()
$folderTarget=[Action]{$script:boundaryEvents.Add('target')}
$folderFocus=[Action]{
    $script:boundaryEvents.Add('focus');$e=New-ExportFolderEvidence;$e.Focus=999
    $e.HasFileNameId=[PixelQuayQualification.ConsumerNative]::IsObservedExportFolderName($e,'Export destination')
    [PixelQuayQualification.ConsumerNative]::ValidateFileName($e)
}
$rejected=$false;try{[PixelQuayQualification.ConsumerNative]::DeliverInput($folderTarget,$folderFocus,$deliver,2)}catch{$rejected=$true}
if(-not $rejected -or ($script:boundaryEvents -join ',') -cne 'target,focus'){throw 'Export folder focus replacement reached native input'}
"PASS $folderTopologyCases export-folder topology cases, $folderGuardCases unchanged filename refusals, and final focus replacement before send"
