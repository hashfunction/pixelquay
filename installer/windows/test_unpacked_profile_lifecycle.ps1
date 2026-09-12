# Execute the actual build script's cleanup block with native/process boundaries substituted.
# Copyright 2026 Trieflow LLC. MIT licensed.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'build-qualification.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Build script does not parse'}
$blocks=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.TryStatementAst] -and $null -ne $node.Finally -and $node.Finally.Extent.Text.Contains('$pixelCleanupErrors=')},$true))
if($blocks.Count -ne 1){throw 'Expected one actual unpackaged cleanup block'}
$text=$blocks[0].Finally.Extent.Text
$actualStartupCleanup=[scriptblock]::Create($text.Substring(1,$text.Length-2))
Add-Type @'
using System.Collections.Generic;
namespace PixelQuayQualification {
public static class ConsumerNative {
 public static Queue<object> Exits=new Queue<object>();
 public static List<int> Waits=new List<int>();
 public static object ExitCode(object process,int timeout) { Waits.Add(timeout); return Exits.Dequeue(); }
}}
'@
$originalLocation=Get-Location
foreach($scenario in @('normal','timeout','unproved-stop','foreign-process','seal-failure','cleanup-failure','early-exit')) {
 $root=Join-Path ([IO.Path]::GetTempPath()) ('pixelquay-startup-lifecycle-'+[guid]::NewGuid().ToString('N'))
 [IO.Directory]::CreateDirectory((Join-Path $root 'build-evidence')) | Out-Null
 try {
  Set-Location $root
  $pixelProcessOwned=$scenario -ne 'foreign-process';$pixelStartupStopped=$false;$pixelNormalClose=$false;$pixelProfileRemoved=$false
  $pixelBuildError='original build context';$pixelStartupState='unused';$pixelPython='unused'
  $calls=[Collections.Generic.List[string]]::new()
  [PixelQuayQualification.ConsumerNative]::Exits.Clear();[PixelQuayQualification.ConsumerNative]::Waits.Clear()
  $values=switch($scenario){'timeout'{@($null,$null,9)} 'unproved-stop'{@($null,$null,$null)} 'early-exit'{@(7)} default{@($null,0)}}
  foreach($value in $values){[PixelQuayQualification.ConsumerNative]::Exits.Enqueue($value)}
  $process=[pscustomobject]@{calls=$calls}
  $process | Add-Member ScriptMethod CloseMainWindow {$this.calls.Add('close');return $true}
  $process | Add-Member ScriptMethod Kill {$this.calls.Add('kill')}
  $process | Add-Member ScriptMethod Dispose {$this.calls.Add('dispose')}
  function Invoke-PixelQuayFiles($operation,$state,$extra,[string]$Python) {
   $calls.Add($operation)
   if(($scenario -eq 'seal-failure' -and $operation -eq 'baseline') -or ($scenario -eq 'cleanup-failure' -and $operation -eq 'cleanup')){throw 'changed owned data'}
   @{removed=$true}
  }
  $failure=$null
  try{. $actualStartupCleanup}catch{$failure=$_.Exception.Message}
  $record=Get-Content 'build-evidence/unpackaged-profile-cleanup.json' -Raw | ConvertFrom-Json
  if($scenario -eq 'normal') {
   if($failure -or -not $record.normal_close_verified -or -not $record.process_stopped -or -not $record.owned_profile_and_fixture_removed){throw 'Normal lifecycle was not verified'}
   if(($calls -join ',') -cne 'close,baseline,cleanup,dispose'){throw 'Normal cleanup order differs'}
  } else {
   if(-not $failure -or $failure -notmatch 'original build context'){throw 'Lifecycle failure lost its primary context'}
   if($scenario -in @('unproved-stop','foreign-process') -and ($calls.Contains('baseline') -or $calls.Contains('cleanup') -or $record.process_stopped)){throw 'Unproved process authorized profile cleanup'}
   if($scenario -eq 'foreign-process' -and ($calls.Count -or [PixelQuayQualification.ConsumerNative]::Waits.Count)){throw 'Foreign process was operated on'}
   if($scenario -eq 'seal-failure' -and $calls.Contains('cleanup')){throw 'Unsealed profile was removed'}
   if($scenario -eq 'timeout' -and (-not $calls.Contains('kill') -or $record.normal_close_verified -or -not $record.process_stopped)){throw 'Timeout must fail normal close but allow cleanup only after proven stop'}
  }
  "PASS actual unpackaged lifecycle: $scenario"
 } finally { Set-Location $originalLocation; Remove-Item -LiteralPath $root -Recurse -Force }
}
