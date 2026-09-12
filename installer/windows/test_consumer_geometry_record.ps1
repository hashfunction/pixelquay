# Copyright 2026 Trieflow LLC. MIT. Production PS evidence path, native reads adapted.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -TypeDefinition @'
using System;
namespace PixelQuayQualification {
 public class ConsumerNative {
  public static bool Refuse=false;public static int Reads=0;
  public static void Require(object app,long main,object target,long window,string title,bool foreground){if(Refuse)throw new Exception("ownership changed");}
  public static object Geometry(object app,long main,object target,long window,string title){Reads++;return new GeometryFixture();}
  public static int[] VisibleBounds(object value){throw new Exception("actual raw bounds refused");}
 }
 public class GeometryFixture {public int[] Window=new[]{0,0,1074,770},Desktop=new[]{0,0,1024,768},WorkArea=new[]{0,0,1024,728};public uint Dpi=96;}
}
'@
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
$processFixture=[pscustomobject]@{Id=4916}
$ui=@{process=$processFixture;main=655474;record=@{geometry=[Collections.Generic.List[object]]::new()}}
$scope=@{process=$processFixture;hwnd=655474;title='source.png - TintFable';class='gdkSurfaceToplevel'}
$failure=$null;try{Save-PixelQuayObservation $ui $scope 'opened'}catch{$failure=$_.Exception.Message}
Check ($failure -match 'actual raw bounds refused') 'The production screenshot route did not preserve bounds refusal.'
Check ($ui.record.geometry.Count -eq 1) 'Clipped capture lost its actual geometry before failing.'
$entry=$ui.record.geometry[0]
Check ($entry.stage -ceq 'opened' -and $entry.hwnd -eq 655474 -and $entry.pid -eq 4916 -and $entry.title -ceq 'source.png - TintFable' -and
    ($entry.window -join ',') -ceq '0,0,1074,770' -and ($entry.desktop -join ',') -ceq '0,0,1024,768' -and
    ($entry.work_area -join ',') -ceq '0,0,1024,728' -and $entry.dpi -eq 96) 'Clipped capture diagnostic values differ from the native observation.'
[PixelQuayQualification.ConsumerNative]::Refuse=$true
$failure=$null;try{Get-PixelQuayGeometry $ui $scope 'unowned'}catch{$failure=$_.Exception.Message}
Check ($failure -match 'ownership changed' -and [PixelQuayQualification.ConsumerNative]::Reads -eq 1 -and $ui.record.geometry.Count -eq 1) 'Ownership refusal still read or recorded a foreign window.'
[PixelQuayQualification.ConsumerNative]::Refuse=$false
foreach($index in 1..63){$null=Get-PixelQuayGeometry $ui $scope "fixture-$index"}
$failure=$null;try{Get-PixelQuayGeometry $ui $scope 'overflow'}catch{$failure=$_.Exception.Message}
Check ($failure -match 'exceeded bound' -and [PixelQuayQualification.ConsumerNative]::Reads -eq 64 -and $ui.record.geometry.Count -eq 64) 'Evidence bound allowed additional native reads or entries.'
Write-Output 'PASS: production screenshot failure retains exact owned geometry before rejecting bounds; ownership and 64-entry diagnostic limit enforced.'
