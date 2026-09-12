# Copyright 2026 Trieflow LLC. MIT. Real snapshot, byte capture and cleanup sequencing.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_library.ps1') -QualifiedSource (Join-Path $PSScriptRoot '../../..')
function Snapshot {return @{process_id=41;main_pid=41;target_pid=41;main=100;target=200;foreground=200;main_title='Cedar Coast.png - TintFable';target_title='Export with Recipe';main_visible=$true;target_visible=$true;dpi=96;
    main_bounds=@(224,50,1472,940);target_bounds=@(400,180,1050,650);work_area=@(0,0,1920,1040);desktop=@(0,0,1920,1080)}}
$script:observations=0;$script:captures=0;$script:change=$false
$ops=@{Observe={$script:observations++;$v=Snapshot;if($script:change -and $script:observations -eq 2){$v.main_bounds[0]++};return $v};Capture={param($bounds)$script:captures++;return ,[byte[]](1,2,3)}}
$r=Invoke-TintFrameCapture $ops 41 100 200 'Cedar Coast.png - TintFable' 'Export with Recipe'
if($script:captures -ne 1 -or $r.bytes.Length -ne 3){throw 'Actual capture callback not used'}
foreach($mutation in @('pid','foreign-main','foreign-target','foreground','title','hidden-main','hidden-target','dpi','width','desktop','clipped-modal')){
    $v=Snapshot
    switch($mutation){pid{$v.process_id=8};foreign-main{$v.main_pid=8};foreign-target{$v.target_pid=8};foreground{$v.foreground=100};title{$v.target_title='Foreign'};hidden-main{$v.main_visible=$false};hidden-target{$v.target_visible=$false};dpi{$v.dpi=144};width{$v.main_bounds[2]=1400};desktop{$v.desktop[2]=1600};clipped-modal{$v.target_bounds[0]=0}}
    $failed=$false;try{Assert-TintFrameSnapshot $v 41 100 200 'Cedar Coast.png - TintFable' 'Export with Recipe'}catch{$failed=$true};if(-not $failed){throw "Unsafe snapshot accepted: $mutation"}
}
$script:change=$true;$script:observations=0;$failed=$false
try{Invoke-TintFrameCapture $ops 41 100 200 'Cedar Coast.png - TintFable' 'Export with Recipe'|Out-Null}catch{$failed=$_.Exception.Message -match 'changed during'}
if(-not $failed){throw 'Moving frame accepted'}
$required=@('Preflight','Prepare','Sign','Install','Activate','Workflow','Close','Uninstall');$cleanup=@('Stop','RestoreDisplay','RemovePackage','RemoveProfileAndDemo','RemoveTrust','RemoveKey','RemoveTemporary')
foreach($failure in @('none')+$required){
    $events=[Collections.Generic.List[string]]::new();$operations=@{}
    foreach($name in $required+$cleanup+@('ObserveFailure')){$n=$name;$operations[$name]={$events.Add($n);if($n -ceq $failure){throw ('failure at '+$n)}}.GetNewClosure()}
    $r=Invoke-TintCaptureLifecycle $operations
    $expected=if($failure -ceq 'none'){$required+$cleanup}else{$required[0..[Array]::IndexOf($required,$failure)]+@('ObserveFailure')+$cleanup}
    if(($events -join '|') -cne ($expected -join '|') -or $r.cleanup_errors.Count -ne 0 -or ($failure -ceq 'none') -ne ($null -eq $r.primary_error)){throw 'Actual lifecycle sequence or primary failure changed'}
}
Write-Output 'PASS real full-window capture, eleven ownership/geometry refusals, mid-frame change, and eight lifecycle failure boundaries.'

$temp=Join-Path ([IO.Path]::GetTempPath()) ('tint-frames-'+[guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($temp)|Out-Null
try{
    $state=@{output=$temp;record=@{sourceCommit=('a'*40)};ownedPackageFullName='assigned';process=@{Id=41};ui=@{main=100};framesVerified=$false}
    foreach($stem in @('01-edited-canvas','02-export-recipe','03-exported-image')){
        $v=Snapshot
        if($stem -cne '02-export-recipe'){$v.target=100;$v.foreground=100;$v.target_bounds=$v.main_bounds;$v.target_title=$v.main_title}
        if($stem -ceq '03-exported-image'){$v.main_title='Cedar Coast-newsletter.png - TintFable';$v.target_title=$v.main_title}
        $path=Join-Path $temp ($stem+'.png');[IO.File]::WriteAllBytes($path,[byte[]](1,2,3))
        Write-NewUtf8Json (Join-Path $temp ($stem+'.json')) @{schema_version=1;pixel_manipulation=$false;consumer_acceptance=$false;process_id=41;qualified_source_commit=('a'*40);package_full_name='assigned';before=$v;after=$v;png=@{bytes=3;sha256=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()}}
    }
    Assert-TintCaptureFrames $state
    if(-not $state.framesVerified){throw 'Real three-frame receipt verification did not complete'}
    [IO.File]::WriteAllBytes((Join-Path $temp '01-edited-canvas.png'),[byte[]](4,5,6));$failed=$false
    try{Assert-TintCaptureFrames $state}catch{$failed=$true};if(-not $failed){throw 'Retained PNG mutation accepted'}
}finally{Remove-Item $temp -Recurse -Force}
Write-Output 'PASS actual retained three-frame identity/hash recheck and changed screenshot refusal.'
