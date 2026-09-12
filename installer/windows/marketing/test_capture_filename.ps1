$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_ui.ps1')
Add-Type @'
namespace PixelQuayQualification {
 public static class ConsumerNative {
  public static int Checks,FailAt,ChordCalls,Pastes; public static bool FailChord;
  public static object FileName(object app,long main,object target,long w,string title,long focus) {
   Checks++;if(focus!=220 || w!=200 || Checks==FailAt)throw new System.InvalidOperationException("Original filename ownership refusal");return null;
  }
  public static void FileNameChord(object app,long main,object target,long w,string title,long focus,int[] keys) {
   FileName(app,main,target,w,title,focus);
   if(keys.Length!=2 || keys[0]!=17 || keys[1]!=86)throw new System.Exception("Expected original Ctrl+V");
   Pastes++;if(FailChord)throw new System.InvalidOperationException("Original guarded paste failure");
  }
  public static void Chord(object app,long main,object target,long w,string title,int[] keys){ChordCalls++;if(FailChord)throw new System.InvalidOperationException("Original chord ownership refusal");}
 }
}
'@
$script:events=[Collections.Generic.List[string]]::new();$script:fail=''
function Assert-PixelQuayScope($Ui,$Scope){$script:events.Add('scope')}
function New-TintFilenameClipboard([string]$Text){
 $script:events.Add('publish')
 if($script:fail -ceq 'publish'){throw 'Initial clipboard is not empty'}
 $lease=[pscustomobject]@{Owner=444;Sequence=19}
 $lease|Add-Member ScriptMethod Verify { $script:events.Add('clipboard-proof');if($script:fail -ceq 'changed'){throw 'Clipboard changed; retained foreign data'} }
 $lease|Add-Member ScriptMethod RestoreEmpty { $script:events.Add('restore');if($script:fail -in @('restore','both')){throw 'Clipboard changed during paste; retained foreign data'} }
 $lease
}
function Wait-PixelQuayFileNameText($Ui,$Scope,[long]$Focus,[string]$Expected) {
 $script:events.Add('readback')
 if($Focus -ne 220 -or $Expected -cne 'C:\TintFable Demo\Cedar Coast.png'){throw 'Original complete-path proof was bypassed'}
 if($script:fail -in @('readback','both')){throw 'Original complete-path readback timeout'}
 $Expected
}
function Start-Sleep([int]$Milliseconds){$script:events.Add('settle:'+ $Milliseconds)}
$scope=@{hwnd=200;title='Save Image File';process=@{Id=17}};$path='C:\TintFable Demo\Cedar Coast.png'
foreach($case in @('pass','before','final-focus','publish','changed','send','readback','restore','both')) {
 $ui=@{process=@{Id=17};main=100;record=@{}};$script:events.Clear();$script:fail=$case
 [PixelQuayQualification.ConsumerNative]::Checks=0;[PixelQuayQualification.ConsumerNative]::Pastes=0
 [PixelQuayQualification.ConsumerNative]::FailAt=switch($case){'before'{1};'final-focus'{2};default{0}}
 [PixelQuayQualification.ConsumerNative]::FailChord=$case -ceq 'send';$caught=$null
 try{Send-PixelQuayFileNameText $ui $scope 220 $path}catch{$caught=$_}
 $expectedPastes=if($case -in @('before','final-focus','publish','changed')){0}else{1}
 if([PixelQuayQualification.ConsumerNative]::Pastes -ne $expectedPastes){throw "Input replayed or bypassed guard: $case"}
 $expectedRestores=if($case -in @('before','publish')){0}else{1}
 if(@($script:events|Where-Object {$_ -ceq 'restore'}).Count -ne $expectedRestores){throw "Clipboard restoration sequence differs: $case"}
 if($case -ceq 'pass') {
  if($caught){throw $caught}
  $record=$ui.record.capture_filename_writes[0]
  if(-not $record.completed -or -not $record.clipboard_restored -or $record.actual -cne $path -or $record.delivery -cne 'Ctrl+V/CF_UNICODETEXT'){throw 'Missing exact paste/readback/restoration evidence'}
  if(($script:events -join '|') -cne 'scope|publish|clipboard-proof|scope|settle:1000|readback|restore'){throw 'Paste proof/readback/restore order differs'}
 }elseif(-not $caught){throw "Failed capture filename accepted: $case"}
 if($case -ceq 'both') {
  if($caught.ToString() -notlike '*Original complete-path readback timeout*' -or $ui.record.capture_filename_writes[0].cleanup_error -notlike '*Clipboard changed during paste*'){throw 'Primary failure or clipboard cleanup failure was lost'}
 }
}
foreach($invalid in @('',('x'*4097),('a'+[char]0+'b'))) {
 $script:events.Clear();$caught=$null
 try{Send-PixelQuayFileNameText @{record=@{}} $scope 220 $invalid}catch{$caught=$_}
 if(-not $caught -or $script:events.Count){throw 'Invalid text reached a native boundary'}
}
$script:events.Clear();$caught=$null
try{Send-PixelQuayFileNameText @{record=@{capture_filename_writes=@(1..8)}} $scope 220 $path}catch{$caught=$_}
if(-not $caught -or $script:events.Count){throw 'Write bound bypassed'}
foreach($failure in @($false,$true)) {
 $script:events.Clear();[PixelQuayQualification.ConsumerNative]::ChordCalls=0;[PixelQuayQualification.ConsumerNative]::FailChord=$failure;$caught=$null
 try{Send-PixelQuayKeys @{process=@{};main=100} $scope @(18,78)}catch{$caught=$_}
 if([PixelQuayQualification.ConsumerNative]::ChordCalls -ne 1 -or ($failure -ne ($null -ne $caught))){throw 'Chord was replayed or original refusal lost'}
 $expected=if($failure){'scope'}else{'scope|settle:1000'}
 if(($script:events -join '|') -cne $expected){throw 'Mnemonic settling occurred in the wrong sequence'}
}
Write-Output 'PASS 15 production paste sequencing, ownership, no-replay, primary/cleanup error, text/count bounds and original one-second chord settling cases.'
