# Copyright 2026 Trieflow LLC. MIT. Exercise production picker selection with replayed UIA nodes.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'consumer_ui.ps1')
Add-Type @'
namespace Windows.Automation {
 public enum TreeScope {Subtree}
 public class Condition {public static Condition TrueCondition=new Condition();}
 public class ReplayCollection {public object[] Nodes;public int Count=>Nodes.Length;public object Item(int i)=>Nodes[i];}
 public class AutomationElement {
  public static AutomationElement Root;public dynamic Current;public ReplayCollection Nodes;
  public static AutomationElement FromHandle(System.IntPtr handle)=>Root;
  public ReplayCollection FindAll(TreeScope scope,Condition condition)=>Nodes;
 }
}
'@
function Assert-PixelQuayScope {param($Ui,$Scope);if($Scope.hwnd -ne 200){throw 'unowned scope'}}
function Node($Name,$Id,$Type='Edit',$OwnerId=17,$Enabled=$true,$Offscreen=$false){
 [pscustomobject]@{Current=[pscustomobject]@{Name=$Name;AutomationId=$Id;ControlType=[pscustomobject]@{ProgrammaticName="ControlType.$Type"};ProcessId=$OwnerId;IsEnabled=$Enabled;IsOffscreen=$Offscreen}}
}
$root=[Windows.Automation.AutomationElement]::new();$root.Current=[pscustomobject]@{NativeWindowHandle=200;ProcessId=17};$root.Nodes=[Windows.Automation.ReplayCollection]::new();[Windows.Automation.AutomationElement]::Root=$root
$scope=@{hwnd=200;process=@{Id=17}}
$filename=Node 'File name:' '1148';$root.Nodes.Nodes=@((Node 'Search Pictures' '1001'),$filename,(Node 'Open' '1' 'Button'))
# Visible Windows screenshot exposes File name:. Its UIA numeric ID is not a supported stable contract.
$actual=Get-PixelQuayPickerControl @{} $scope '' 'Edit' -Names @('File name:','Folder:')
if(-not [object]::ReferenceEquals($actual,$filename)){throw 'Did not select uniquely labelled filename instead of numeric-ID search field'}
$count=1
foreach($id in @('1001','1148','provider-name')){
 $root.Nodes.Nodes=@((Node 'Folder:' $id));$null=Get-PixelQuayPickerControl @{} $scope '' 'Edit' -Names @('File name:','Folder:');$count++
}
foreach($nodes in @(
 @((Node 'Search Pictures' '1001')),
 @((Node 'File name:' '1148'),(Node 'Folder:' '1001')),
 @((Node 'File name:' '1148' 'Button')),
 @((Node 'File name:' '1148' 'Edit' 99)),
 @((Node 'File name:' '1148' 'Edit' 17 $false)),
 @((Node 'File name:' '1148' 'Edit' 17 $true $true))
)){
 $root.Nodes.Nodes=$nodes;$failed=$false;try{$null=Get-PixelQuayPickerControl @{} $scope '' 'Edit' -Names @('File name:','Folder:')}catch{$failed=$true};if(-not $failed){throw 'Accepted absent/ambiguous/foreign/disabled/hidden filename'};$count++
}
$root.Nodes.Nodes=@((Node 'Open' '1' 'Button'),(Node 'Cancel' '2' 'Button'));$selected=Get-PixelQuayPickerControl @{} $scope '1' 'Button';if($selected.Current.Name -cne 'Open'){throw 'Existing exact primary button selection regressed'}
"PASS $($count+1) production picker selection cases; native UIA observations still require Windows."
