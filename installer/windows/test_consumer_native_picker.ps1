# Production path-entry sequencing with a replayed native observer; no Win32 calls here.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
Add-Type @'
namespace PixelQuayQualification {
 public class ObservedName {public long Focus=220;public string Class="Edit";public bool HasFileNameId=true;}
 public class ObservedChoice {public long Button=230;}
 public static class ConsumerNative {
  public static int Calls,FailAt,BoundaryCalls,FailBoundaryAt;public static string Readback;public static System.Collections.Generic.List<string> Events=new System.Collections.Generic.List<string>();
  public static ObservedName FileName(object app,long main,object target,long w,string title,long expected){Calls++;if(Calls==FailAt)throw new System.InvalidOperationException("focus changed");return new ObservedName();}
  public static int ReadCalls,FailReadAt;public static string[] PendingReadbacks=System.Array.Empty<string>();
  public static string FileNameText(object app,long main,object target,long w,string title,long focus){
   ReadCalls++;if(focus!=220 || w!=200)throw new System.InvalidOperationException("readback lost retained identity");if(ReadCalls==FailReadAt)throw new System.InvalidOperationException("readback focus changed");
   return ReadCalls<=PendingReadbacks.Length?PendingReadbacks[ReadCalls-1]:Readback;
  }
  static void Boundary(long expected){BoundaryCalls++;if(expected!=220 || BoundaryCalls==FailBoundaryAt)throw new System.InvalidOperationException("focus changed at native input");}
  public static void FileNameChord(object app,long main,object target,long w,string title,long expected,int[] keys){Boundary(expected);Events.Add("keys:"+string.Join(",",keys));}
  public static void FileNameTextInput(object app,long main,object target,long w,string title,long expected,string text){Boundary(expected);Events.Add("text:"+text);}
  public static int ChooseCalls,FailChooseAt;public static bool FailChooseSend;
  public static ObservedChoice ExportChoose(object app,long main,object target,long w,string title,long filename,string path,object retained,bool focused){
   ChooseCalls++;Events.Add(focused?"observe-focused-choose":"observe-choose-before-tab");
   if(ChooseCalls==FailChooseAt)throw new System.InvalidOperationException("Choose ownership differs");
   if(title!="Export destination" || filename!=220 || path!=Readback || (focused && retained==null))throw new System.InvalidOperationException("Missing retained Choose state");
   return new ObservedChoice();
  }
  public static void ExportChooseSpace(object app,long main,object target,long w,string title,long filename,string path,object retained){
   Events.Add("choose-native-boundary");if(FailChooseSend)throw new System.InvalidOperationException("Choose focus moved before input");
   if(retained==null)throw new System.InvalidOperationException("Missing Choose");Events.Add("keys:32");
  }

  public static long[] Windows(long main)=>new long[]{main};
 }
}
'@
$script:events=[PixelQuayQualification.ConsumerNative]::Events
function Assert-PixelQuayScope {param($Ui,$Scope)}
$scope=@{hwnd=200;title='Open Image File';process=@{Id=17}}
function Get-PixelQuayScope {param($Ui,$Title,[switch]$Picker);$scope}
function Send-PixelQuayKeys {param($Ui,$Scope,[int[]]$Keys);$script:events.Add('keys:'+($Keys -join ','))}
function Send-PixelQuayText {param($Ui,$Scope,[string]$Text);$script:events.Add('text:'+$Text)}
function Save-PixelQuayObservation {param($Ui,$Scope,$Stage);$script:events.Add('capture')}
# Advance a monotonic test clock without spending 30 seconds on every refusal.
$script:milliseconds=0
function Get-PixelQuayConsumerMonotonicMilliseconds { return $script:milliseconds }
function Start-Sleep {param([int]$Milliseconds);$script:milliseconds+=$Milliseconds}
$path='C:\owned\images\résumé.png'
foreach($case in @('pass','focus-after-alt-n','focus-before-text','focus-before-enter','wrong-readback','boundary-select-all','boundary-text','boundary-enter')) {
 $script:milliseconds=0;[PixelQuayQualification.ConsumerNative]::ReadCalls=0
 $script:events.Clear();[PixelQuayQualification.ConsumerNative]::Calls=0
 [PixelQuayQualification.ConsumerNative]::BoundaryCalls=0
 [PixelQuayQualification.ConsumerNative]::FailBoundaryAt=switch($case){'boundary-select-all'{1};'boundary-text'{2};'boundary-enter'{3};default{0}}
 [PixelQuayQualification.ConsumerNative]::FailAt=switch($case){'focus-after-alt-n'{1};'focus-before-text'{2};'focus-before-enter'{3};default{0}}
 [PixelQuayQualification.ConsumerNative]::Readback=if($case -eq 'wrong-readback'){'C:\foreign\wrong.png'}else{$path}
 $ui=@{process=@{Id=17};main=100;record=@{picker_fields=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
 $failed=$false;try{Set-PixelQuayPickerPath $ui 'Open Image File' $path}catch{$failed=$true}
 if($case -eq 'pass') {
  if($failed -or ($script:events -join '|') -cne ('keys:18,78|keys:17,65|text:'+$path+'|capture|keys:13')){throw 'Exact native filename sequence differed'}
 } else {
  if(-not $failed -or 'keys:13' -in $script:events){throw 'Unverified filename was submitted'}
  $expectedStage=switch($case){
   'focus-after-alt-n'{'observe-after-alt-n'};'focus-before-text'{'observe-before-text'};'focus-before-enter'{'observe-before-enter'};
   'wrong-readback'{'readback-filename'};'boundary-select-all'{'select-filename'};'boundary-text'{'type-filename'};'boundary-enter'{'submit-filename'}
  }
  $saved=$ui.record|ConvertTo-Json -Depth 12|ConvertFrom-Json
  if($saved.picker_failures.Count -ne 1 -or $saved.picker_failures[0].stage -cne $expectedStage -or $saved.picker_failures[0].hwnd -ne 200){throw 'Refusing picker stage was not retained in JSON'}
  if($case -eq 'focus-after-alt-n' -and (($script:events -join '|') -cne 'keys:18,78' -or $saved.picker_failures[0].expected_focus -ne 0)){throw 'Unproven initial filename received input or acquired retained focus'}
  if($case -in @('focus-after-alt-n','focus-before-text','boundary-select-all','boundary-text') -and @($script:events|Where-Object {$_ -like 'text:*'}).Count){throw 'Typed after focus left filename'}
 }
}
'PASS8 actual picker sequencing and native-boundary refusal cases; physical Windows execution pending'

# A single native text send may still be queued when the first WM_GETTEXT is
# served. Exercise the real production convergence loop, never replay the send.
foreach($case in @('pending-prefix','empty-then-exact','persistent-wrong','focus-during-readback','deadline-exact')) {
 $script:milliseconds=0;$script:events.Clear()
 [PixelQuayQualification.ConsumerNative]::Calls=0;[PixelQuayQualification.ConsumerNative]::FailAt=0
 [PixelQuayQualification.ConsumerNative]::BoundaryCalls=0;[PixelQuayQualification.ConsumerNative]::FailBoundaryAt=0
 [PixelQuayQualification.ConsumerNative]::ReadCalls=0
 [PixelQuayQualification.ConsumerNative]::FailReadAt=if($case -ceq 'focus-during-readback'){2}else{0}
 [PixelQuayQualification.ConsumerNative]::PendingReadbacks=@(switch($case){
  'pending-prefix'{@('C:\','C:\owned\images\rés')};'empty-then-exact'{@('')};
  'focus-during-readback'{@('C:\')};default{@()}
 })
 [PixelQuayQualification.ConsumerNative]::Readback=if($case -ceq 'persistent-wrong'){'C:\foreign\wrong.png'}else{$path}
 # A slow native query returning exact text after its deadline cannot pass.
 function Get-PixelQuayConsumerMonotonicMilliseconds {
  if($case -ceq 'deadline-exact' -and [PixelQuayQualification.ConsumerNative]::ReadCalls -gt 0){return 30000}
  return $script:milliseconds
 }
 $ui=@{process=@{Id=17};main=100;record=@{picker_fields=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
 $failed=$false;try{Set-PixelQuayPickerPath $ui 'Open Image File' $path}catch{$failed=$true}
 $saved=$ui.record|ConvertTo-Json -Depth 14|ConvertFrom-Json
 if($saved.picker_readbacks.Count -ne 1){throw 'Actual readback evidence missing'}
 $proof=$saved.picker_readbacks[0]
 if($proof.expected -cne $path -or $proof.focus -ne 220 -or $proof.hwnd -ne 200 -or $proof.pid -ne 17 -or $proof.timeout_ms -ne 30000){throw 'Readback identity/expected/deadline missing'}
 if(@($script:events|Where-Object {$_ -like 'text:*'}).Count -ne 1 -or @($script:events|Where-Object {$_ -ceq 'keys:17,65'}).Count -ne 1){throw 'Readback wait replayed filename input'}
 if($case -in @('pending-prefix','empty-then-exact')){
  $count=if($case -ceq 'pending-prefix'){3}else{2}
  if($failed -or [PixelQuayQualification.ConsumerNative]::ReadCalls -ne $count -or $proof.observations.Count -ne $count -or $proof.observations[-1].value -cne $path -or 'keys:13' -notin $script:events){throw 'Exact queued text was not observed before one submit'}
  if($case -ceq 'pending-prefix' -and ($proof.observations.value -join '|') -cne ('C:\|C:\owned\images\rés|'+$path)){throw 'Pending native values were not preserved exactly'}
 }else{
  if(-not $failed -or 'keys:13' -in $script:events -or 'capture' -in $script:events){throw 'Failed/expired readback reached capture or submission'}
  if($saved.picker_failures[0].stage -cne 'readback-filename'){throw 'Readback failure stage lost'}
  if($case -ceq 'persistent-wrong' -and ([PixelQuayQualification.ConsumerNative]::ReadCalls -ne 300 -or $proof.observations.Count -ne 300 -or $proof.observations[-1].value -cne 'C:\foreign\wrong.png')){throw "Persistent mismatch differed: reads=$([PixelQuayQualification.ConsumerNative]::ReadCalls) observations=$($proof.observations.Count) elapsed=$script:milliseconds last=$($proof.observations[-1].value)"}
  if($case -ceq 'focus-during-readback' -and ([PixelQuayQualification.ConsumerNative]::ReadCalls -ne 2 -or $proof.observations.Count -ne 1 -or $script:milliseconds -ne 100)){throw 'Native focus refusal was retried or swallowed'}
  if($case -ceq 'deadline-exact' -and ($proof.observations.Count -ne 1 -or $proof.observations[0].elapsed_ms -ne 30000)){throw 'Expired exact readback was not recorded/refused'}
 }
}
[PixelQuayQualification.ConsumerNative]::PendingReadbacks=@();[PixelQuayQualification.ConsumerNative]::FailReadAt=0
function Get-PixelQuayConsumerMonotonicMilliseconds {return $script:milliseconds}
'PASS five actual bounded readback convergence, evidence and no-replay refusal cases'

$scope.title='Export destination'
foreach($case in @('pass','unproved-choose','tab-focus-boundary','wrong-focused-button','native-button-changed')) {
 $script:milliseconds=0;[PixelQuayQualification.ConsumerNative]::ReadCalls=0
 $script:events.Clear();[PixelQuayQualification.ConsumerNative]::Calls=0;[PixelQuayQualification.ConsumerNative]::FailAt=0
 [PixelQuayQualification.ConsumerNative]::BoundaryCalls=0;[PixelQuayQualification.ConsumerNative]::FailBoundaryAt=if($case -ceq 'tab-focus-boundary'){3}else{0}
 [PixelQuayQualification.ConsumerNative]::ChooseCalls=0;[PixelQuayQualification.ConsumerNative]::FailChooseAt=switch($case){'unproved-choose'{1};'wrong-focused-button'{2};default{0}}
 [PixelQuayQualification.ConsumerNative]::FailChooseSend=$case -ceq 'native-button-changed';[PixelQuayQualification.ConsumerNative]::Readback=$path
 $ui=@{process=@{Id=17};main=100;record=@{picker_fields=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
 $failed=$false;try{Set-PixelQuayPickerPath $ui 'Export destination' $path}catch{$failed=$true}
 if($case -ceq 'pass'){
  if($failed -or ($script:events -join '|') -cne ('keys:18,78|keys:17,65|text:'+$path+'|capture|observe-choose-before-tab|keys:9|observe-focused-choose|choose-native-boundary|keys:32')){throw 'Exact ordinary folder Choose sequence differs'}
  if($ui.record.picker_buttons.Count -ne 3){throw 'Actual queried button metadata/input receipt missing'}
 }else{
  if(-not $failed -or 'keys:32' -in $script:events -or 'keys:13' -in $script:events){throw 'Unproved Choose received activation'}
  $expected=switch($case){'unproved-choose'{'observe-choose-before-tab'};'tab-focus-boundary'{'tab-to-choose'};'wrong-focused-button'{'observe-focused-choose'};'native-button-changed'{'activate-choose'}}
  if($ui.record.picker_failures[0].stage -cne $expected){throw 'Choose refusal phase missing'}
  if($case -ceq 'unproved-choose' -and 'keys:9' -in $script:events){throw 'Tab sent before query proved the Choose control'}
 }
}
$scope.title='Open Image File'
'PASS five actual folder Choose sequence/stop cases; queried Windows ID remains pending'

# A diagnostic serialization/recording failure cannot mask the input refusal.
$script:milliseconds=0;[PixelQuayQualification.ConsumerNative]::ReadCalls=0
$script:events.Clear();[PixelQuayQualification.ConsumerNative]::Calls=0;[PixelQuayQualification.ConsumerNative]::FailAt=1
$ui=@{process=@{Id=17};main=100;record=@{picker_fields=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
function Save-PixelQuayFileNameFailure {throw 'diagnostic recording failed'}
$message=$null;try{Set-PixelQuayPickerPath $ui 'Save Image File' $path}catch{$message=$_.Exception.Message}
if($message -notlike '*focus changed*' -or $ui.record.picker_failure_evidence_error -cne 'diagnostic recording failed' -or ($script:events -join '|') -cne 'keys:18,78'){throw 'Diagnostic error replaced primary refusal or allowed input'}
'PASS original native refusal remains primary when diagnostic recording fails'
