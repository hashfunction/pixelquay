# Production path-entry sequencing with a replayed native observer; no Win32 calls here.
# Copyright 2026 Trieflow LLC. MIT.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
Add-Type @'
namespace PixelQuayQualification {
 public class ObservedName {public long Focus=220;public string Class="Edit";public bool HasFileNameId=true;}
 public static class ConsumerNative {
  public static int Calls,FailAt,BoundaryCalls,FailBoundaryAt;public static string Readback;public static System.Collections.Generic.List<string> Events=new System.Collections.Generic.List<string>();
  public static ObservedName FileName(object app,long main,object target,long w,string title,long expected){Calls++;if(Calls==FailAt)throw new System.InvalidOperationException("focus changed");return new ObservedName();}
  public static string FileNameText(object app,long main,object target,long w,string title,long focus)=>Readback;
  static void Boundary(long expected){BoundaryCalls++;if(expected!=220 || BoundaryCalls==FailBoundaryAt)throw new System.InvalidOperationException("focus changed at native input");}
  public static void FileNameChord(object app,long main,object target,long w,string title,long expected,int[] keys){Boundary(expected);Events.Add("keys:"+string.Join(",",keys));}
  public static void FileNameTextInput(object app,long main,object target,long w,string title,long expected,string text){Boundary(expected);Events.Add("text:"+text);}

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
$path='C:\owned\images\résumé.png'
foreach($case in @('pass','focus-before-text','focus-before-enter','wrong-readback','boundary-select-all','boundary-text','boundary-enter')) {
 $script:events.Clear();[PixelQuayQualification.ConsumerNative]::Calls=0
 [PixelQuayQualification.ConsumerNative]::BoundaryCalls=0
 [PixelQuayQualification.ConsumerNative]::FailBoundaryAt=switch($case){'boundary-select-all'{1};'boundary-text'{2};'boundary-enter'{3};default{0}}
 [PixelQuayQualification.ConsumerNative]::FailAt=switch($case){'focus-before-text'{2};'focus-before-enter'{3};default{0}}
 [PixelQuayQualification.ConsumerNative]::Readback=if($case -eq 'wrong-readback'){'C:\foreign\wrong.png'}else{$path}
 $ui=@{process=@{Id=17};main=100;record=@{picker_fields=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
 $failed=$false;try{Set-PixelQuayPickerPath $ui 'Open Image File' $path}catch{$failed=$true}
 if($case -eq 'pass') {
  if($failed -or ($script:events -join '|') -cne ('keys:18,78|keys:17,65|text:'+$path+'|capture|keys:13')){throw 'Exact native filename sequence differed'}
 } else {
  if(-not $failed -or 'keys:13' -in $script:events){throw 'Unverified filename was submitted'}
  if($case -in @('focus-before-text','boundary-select-all','boundary-text') -and @($script:events|Where-Object {$_ -like 'text:*'}).Count){throw 'Typed after focus left filename'}
 }
}
'PASS7 actual picker sequencing and native-boundary refusal cases; physical Windows execution pending'
