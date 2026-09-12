$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_ui.ps1')
Add-Type @'
namespace PixelQuayQualification {
 public static class ConsumerNative {
  public static string Value="before"; public static int Checks,FailAt,ChordCalls; public static bool FailChord;
  public static object FileName(object app,long main,object target,long w,string title,long focus) {
   Checks++;if(focus!=220 || w!=200 || Checks==FailAt)throw new System.InvalidOperationException("Original filename ownership refusal");return null;
  }
  public static string FileNameText(object app,long main,object target,long w,string title,long focus){return Value;}
  public static void FileNameTextInput(object app,long main,object target,long w,string title,long focus,string text){Value+=text;}
  public static void Chord(object app,long main,object target,long w,string title,int[] keys){ChordCalls++;if(FailChord)throw new System.InvalidOperationException("Original chord ownership refusal");}
 }
}
'@
$script:events=[Collections.Generic.List[string]]::new();$script:fail=''
function Assert-PixelQuayScope($Ui,$Scope){$script:events.Add('scope')}
function Set-TintNativeFilename([long]$Window,[string]$Text){
 $script:events.Add('set:'+ $Text)
 if($Window -ne 220){throw 'Wrong native target'}
 if($script:fail -ceq 'send'){throw 'Original native send timeout'}
 [PixelQuayQualification.ConsumerNative]::Value=if($script:fail -ceq 'readback'){'partial'}else{$Text}
}
$scope=@{hwnd=200;title='Save Image File';process=@{Id=17}};$path='C:\TintFable Demo\Cedar Coast.png'
foreach($case in @('pass','before','after','send','readback')) {
 $ui=@{process=@{Id=17};main=100;record=@{}};$script:events.Clear();$script:fail=$case
 [PixelQuayQualification.ConsumerNative]::Checks=0;[PixelQuayQualification.ConsumerNative]::FailAt=switch($case){'before'{1};'after'{2};default{0}}
 $caught=$null
 try{Send-PixelQuayFileNameText $ui $scope 220 $path}catch{$caught=$_}
 $writes=@($script:events|Where-Object {$_ -like 'set:*'})
 if($case -ceq 'pass') {
  if($caught){throw $caught}
  if($writes.Count -ne 1 -or -not $ui.record.Contains('capture_filename_writes') -or $ui.record.capture_filename_writes[0].actual -cne $path -or [PixelQuayQualification.ConsumerNative]::Checks -ne 2){throw 'Exact one-shot write/readback was not retained'}
 }else{
  if(-not $caught -or $ui.record.Contains('capture_filename_writes')){throw 'Failed native filename accepted'}
  $expected=if($case -ceq 'before'){0}else{1}
  if($writes.Count -ne $expected){throw 'Native input replayed or occurred after failed ownership'}
 }
}
Write-Output 'PASS one exact native filename write/readback and four ownership/send/readback failures without replay.'
foreach($invalid in @('',('x'*4097),('a'+[char]0+'b'))) {
 $script:events.Clear();$caught=$null
 try{Send-PixelQuayFileNameText @{record=@{}} $scope 220 $invalid}catch{$caught=$_}
 if(-not $caught -or $script:events.Count){throw 'Invalid text reached a native boundary'}
}
function Start-Sleep([int]$Milliseconds){$script:events.Add('settle:'+ $Milliseconds)}
foreach($failure in @($false,$true)) {
 $script:events.Clear();[PixelQuayQualification.ConsumerNative]::ChordCalls=0;[PixelQuayQualification.ConsumerNative]::FailChord=$failure;$caught=$null
 try{Send-PixelQuayKeys @{process=@{};main=100} $scope @(18,78)}catch{$caught=$_}
 if([PixelQuayQualification.ConsumerNative]::ChordCalls -ne 1 -or ($failure -ne ($null -ne $caught))){throw 'Chord was replayed or original refusal lost'}
 $expected=if($failure){'scope'}else{'scope|settle:1000'}
 if(($script:events -join '|') -cne $expected){throw 'Mnemonic settling occurred in the wrong sequence'}
}
Add-Type -Path (Join-Path $PSScriptRoot 'capture_filename.cs')
[TintFableMarketing.Filename]::Validate(220,'C:\native\résumé.png')
foreach($invalid in @(@(0,'path'),@(-1,'path'),@(65535,'path'),@(220,''),@(220,('x'*4097)),@(220,('a'+[char]0+'b')))) {
 $caught=$null;try{[TintFableMarketing.Filename]::Set($invalid[0],$invalid[1])}catch{$caught=$_}
 if(-not $caught -or $caught.Exception.ToString() -notlike '*Invalid bounded native filename target/text*'){throw 'Invalid native target/text reached Win32 or lost its refusal'}
}
Write-Output 'PASS bounded text, one-shot mnemonic settling, compiled native Unicode validation and six native target/text refusals; actual WM_SETTEXT execution remains pending Windows.'
