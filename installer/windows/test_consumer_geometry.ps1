# Copyright 2026 Trieflow LLC. MIT. Real production geometry and final mutation guard.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'consumer_native.cs')
function Check($Value,[string]$Message){if(-not $Value){throw $Message}}
function Geometry([int[]]$Window=@(224,50,1472,940),[int[]]$Desktop=@(0,0,1920,1080),[int[]]$Work=@(0,0,1920,1040),[uint32]$Dpi=96){
    $g=[PixelQuayQualification.ConsumerGeometry]::new();$g.Window=$Window;$g.Desktop=$Desktop;$g.WorkArea=$Work;$g.Dpi=$Dpi;return $g
}
function Reject([scriptblock]$Action,[string]$Message){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed $Message}
Check ($null -ne ('PixelQuayQualification.ConsumerGeometry' -as [type])) 'Production geometry evidence is missing; clipped failure cannot retain actual rect/desktop/DPI.'
$monitor=[PixelQuayQualification.ConsumerNative].GetNestedType('MONITORINFO',[Reflection.BindingFlags]::NonPublic)
Check ([Runtime.InteropServices.Marshal]::SizeOf([Activator]::CreateInstance($monitor)) -eq 40) 'Native monitor structure layout differs.'
$g=Geometry
Check (([PixelQuayQualification.ConsumerNative]::VisibleBounds($g) -join ',') -ceq '224,50,1472,940,0,0,1920,1080') 'Actual visible bounds changed.'
Check (([PixelQuayQualification.ConsumerNative]::PlacementPlan($g) -join ',') -ceq '224,50,1472,940') 'Actual work-area centering failed.'
$negative=Geometry @(0,0,1472,940) @(-1920,0,3840,1080) @(-1920,0,1920,1040)
Check (([PixelQuayQualification.ConsumerNative]::PlacementPlan($negative) -join ',') -ceq '-1696,50,1472,940') 'Negative-origin monitor placement failed.'
foreach($window in @(@(-1,0,1472,940),@(449,0,1472,940),@(0,141,1472,940),@(0,0,0,940),@(0,0,4001,4000))){
    Reject { [PixelQuayQualification.ConsumerNative]::VisibleBounds((Geometry $window)) } 'Out-of-bounds/empty/oversized raw window was accepted.'
}
$message=$null;try{[PixelQuayQualification.ConsumerNative]::VisibleBounds((Geometry @(0,0,1074,770) @(0,0,1024,768) @(0,0,1024,728))) }catch{$message=$_.Exception.Message}
Check ($message -match '1074,770' -and $message -match '1024,768' -and $message -match 'dpi=96') 'Original clipped geometry failure lost exact diagnostic values.'
Reject { [PixelQuayQualification.ConsumerNative]::PlacementPlan((Geometry @(0,0,1074,770) @(0,0,1024,768) @(0,0,1024,728))) } 'Unsupported small desktop was silently cropped.'
Reject { [PixelQuayQualification.ConsumerNative]::PlacementPlan((Geometry @(0,0,1472,940) @(0,0,1920,1080) @(0,0,1921,1040))) } 'Work area outside actual desktop accepted.'
Reject { [PixelQuayQualification.ConsumerNative]::VisibleBounds((Geometry -Dpi 0)) } 'Unknown DPI accepted.'
Reject { [PixelQuayQualification.ConsumerNative]::VisibleBounds((Geometry -Dpi 144)) } 'Unqualified scaled capture coordinates accepted.'
Reject { [PixelQuayQualification.ConsumerNative]::PlacedBounds((Geometry @(224,50,1100,750))) } 'Placement accepted unreadably small actual window.'
Reject { [PixelQuayQualification.ConsumerNative]::PlacedBounds((Geometry @(224,120,1472,940))) } 'Placement accepted a window overlapping taskbar work area.'
Check (([PixelQuayQualification.ConsumerNative]::PlacedBounds($g) -join ',') -ceq '224,50,1472,940,0,0,1920,1080') 'Readable fully visible window rejected.'
[PixelQuayQualification.ConsumerNative]::ValidatePlacementTarget(123,123,$true,'gdkSurfaceToplevel')
Reject { [PixelQuayQualification.ConsumerNative]::ValidatePlacementTarget(123,456,$true,'gdkSurfaceToplevel') } 'Owned child could be moved as root.'
Reject { [PixelQuayQualification.ConsumerNative]::ValidatePlacementTarget(123,123,$false,'gdkSurfaceToplevel') } 'Reacquired or picker process could be moved.'
Reject { [PixelQuayQualification.ConsumerNative]::ValidatePlacementTarget(123,123,$true,'#32770') } 'Picker could be moved as GTK root.'
$script:calls=[Collections.Generic.List[string]]::new()
[PixelQuayQualification.ConsumerNative]::DeliverPlacement([Action]{$script:calls.Add('require-owned-root')},[Func[bool]]{$script:calls.Add('move');return $true})
Check (($script:calls -join ',') -ceq 'require-owned-root,move') 'Final ownership guard did not immediately precede native placement.'
$script:calls.Clear()
Reject { [PixelQuayQualification.ConsumerNative]::DeliverPlacement([Action]{throw 'ownership changed'},[Func[bool]]{$script:calls.Add('unsafe-move');return $true}) } 'Changed root ownership did not refuse placement.'
Check ($script:calls.Count -eq 0) 'Native placement ran after ownership rejection.'
Reject { [PixelQuayQualification.ConsumerNative]::DeliverPlacement([Action]{},[Func[bool]]{return $false}) } 'Native placement failure accepted.'
Write-Output 'PASS: actual geometry planning/visibility, clipped diagnostic retention, negative monitor origin, DPI/work-area gates, readable placement, and final ownership-before-move boundary.'
