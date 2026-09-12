# Copyright 2026 Trieflow LLC. MIT. Capture only, using qualified native ownership.
function Add-TintCaptureTypes {
    if('TintFableMarketing.Frame' -as [type]){return}
    Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
namespace TintFableMarketing {
 public static class Frame {
  [StructLayout(LayoutKind.Sequential)]public struct RECT{public int Left,Top,Right,Bottom;}
  [DllImport("user32.dll",SetLastError=true)]static extern bool GetWindowRect(IntPtr hwnd,out RECT rectangle);
  [DllImport("user32.dll")]public static extern bool IsWindowVisible(IntPtr hwnd);
  [DllImport("user32.dll")]static extern bool IsZoomed(IntPtr hwnd);
  [DllImport("user32.dll")]static extern bool ShowWindowAsync(IntPtr hwnd,int state);
  public static bool Maximized(long hwnd){return IsZoomed((IntPtr)hwnd);}
  public static bool Maximize(long hwnd){return ShowWindowAsync((IntPtr)hwnd,3);}
  public static bool Visible(long hwnd){return IsWindowVisible((IntPtr)hwnd);}
  public static int[] Rect(long hwnd){RECT r;if(!GetWindowRect((IntPtr)hwnd,out r))throw new InvalidOperationException("Native main rectangle unavailable");return new[]{r.Left,r.Top,checked(r.Right-r.Left),checked(r.Bottom-r.Top)};}
 }
}
'@
}
function Set-TintMaximizedPlacement($Ui,$Scope) {
    Add-TintCaptureTypes
    Assert-TintCaptureProcess $Ui.state;Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::ValidatePlacementTarget($Ui.main,$Scope.hwnd,[Object]::ReferenceEquals($Ui.process,$Scope.process),$Scope.class)
    if(-not [TintFableMarketing.Frame]::Maximize($Ui.main)){throw 'Native maximize request failed'}
    Wait-PixelQuayConsumer {
        $snapshot=Get-TintFrameSnapshot $Ui $Scope
        if(-not $snapshot.main_maximized){return $false}
        Assert-TintFrameSnapshot $snapshot $Ui.process.Id $Ui.main $Ui.main $Scope.title $Scope.title
        return $true
    } 'actual maximized editor covering its work area' | Out-Null
}
function Assert-TintCaptureProcess($State) {
    $process=$State.process
    if($process.SafeHandle.IsClosed -or $process.SafeHandle.IsInvalid -or $process.HasExited -or
       [PixelQuayQualification.NativePackageProbe]::GetFullName($process.Handle) -cne $State.ownedPackageFullName -or
       (Get-CanonicalPath $process.Path) -cne (Get-CanonicalPath (Join-Path $State.installed.InstallLocation 'bin/TintFable.exe'))){throw 'Retained capture package/process path differs'}
    $null=Assert-FileMatchesRecord $process.Path (Get-RecordPayloadEntry $State.record 'bin/TintFable.exe') 'Actual capture executable'
}
function Get-TintCaptureModules($State) {
    Assert-TintCaptureProcess $State;$State.process.Refresh()
    $installRoot=Get-CanonicalPath $State.installed.InstallLocation;$windowsRoot=Get-CanonicalPath $env:SystemRoot
    $result=[Collections.Generic.List[object]]::new();$required=@('bin/TintFable.exe','bin/coreclr.dll','bin/hostfxr.dll')
    foreach($module in @($State.process.Modules)){
        $path=Get-CanonicalPath $module.FileName
        if(Test-PathInside $path $installRoot){
            $relative=$path.Substring($installRoot.Length).TrimStart('\','/').Replace('\','/')
            $hash=Assert-FileMatchesRecord $path (Get-RecordPayloadEntry $State.record $relative) 'Actual loaded module'
            $origin='package';$required=@($required|Where-Object {$_ -cne $relative})
        }elseif(Test-PathInside $path $windowsRoot){$relative=$null;$hash=$null;$origin='windows'}else{throw 'Captured process loaded a foreign module'}
        $result.Add(@{name=$module.ModuleName;path=$path;relative_path=$relative;sha256=$hash;origin=$origin})
    }
    if($required.Count){throw 'Capture did not load every required packaged runtime module'}
    return ,@($result)
}
function Assert-TintFrameSnapshot($Value,[int]$ExpectedPid,[long]$Main,[long]$Target,[string]$MainTitle,[string]$TargetTitle) {
    if($Value.process_id -ne $ExpectedPid -or $Value.main_pid -ne $ExpectedPid -or $Value.target_pid -ne $ExpectedPid -or
        $Value.main -ne $Main -or $Value.target -ne $Target -or $Value.foreground -ne $Target -or
        $Value.main_title -cne $MainTitle -or $Value.target_title -cne $TargetTitle -or -not $Value.main_visible -or -not $Value.target_visible -or $Value.dpi -ne 96){throw 'Capture surface ownership/title/foreground differs'}
    $m=$Value.main_bounds;$t=$Value.target_bounds;$a=$Value.work_area;$d=$Value.desktop;$c=$Value.capture_bounds
    foreach($r in @($m,$t,$a,$d,$c)){if($r.Count -ne 4 -or $r[2] -le 0 -or $r[3] -le 0){throw 'Invalid capture rectangle'}}
    if(-not $Value.main_maximized -or $a[2] -lt 1920 -or $a[3] -lt 1000 -or $d[2] -lt 1920 -or $d[3] -lt 1080 -or ($c -join ',') -cne ($a -join ',')){throw 'Actual maximized marketing resolution differs'}
    if($a[0] -lt $d[0] -or $a[1] -lt $d[1] -or $a[0]+$a[2] -gt $d[0]+$d[2] -or $a[1]+$a[3] -gt $d[1]+$d[3] -or $m[0] -gt $a[0] -or $m[1] -gt $a[1] -or $m[0]+$m[2] -lt $a[0]+$a[2] -or $m[1]+$m[3] -lt $a[1]+$a[3]){throw 'Maximized editor does not cover the visible work area'}
    if($Target -eq $Main){if(($t -join ',') -cne ($m -join ',')){throw 'Main target rectangle differs'}}
    elseif($t[0] -lt $a[0] -or $t[1] -lt $a[1] -or $t[0]+$t[2] -gt $a[0]+$a[2] -or $t[1]+$t[3] -gt $a[1]+$a[3]){throw 'Owned dialog lies outside the captured editor'}
}
function Get-TintFrameSnapshot($Ui,$Scope) {
    Assert-TintCaptureProcess $Ui.state;Assert-PixelQuayScope $Ui $Scope
    $geometry=[PixelQuayQualification.ConsumerNative]::Geometry($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title)
    return @{process_id=$Ui.process.Id;main_pid=[PixelQuayQualification.ConsumerNative]::Pid($Ui.main);target_pid=[PixelQuayQualification.ConsumerNative]::Pid($Scope.hwnd);
        main=$Ui.main;target=$Scope.hwnd;foreground=[PixelQuayQualification.ConsumerNative]::ForegroundWindow();
        main_title=[PixelQuayQualification.ConsumerNative]::Title($Ui.main);target_title=[PixelQuayQualification.ConsumerNative]::Title($Scope.hwnd);
        main_visible=[TintFableMarketing.Frame]::Visible($Ui.main);target_visible=[TintFableMarketing.Frame]::Visible($Scope.hwnd);
        main_maximized=[TintFableMarketing.Frame]::Maximized($Ui.main);capture_bounds=$geometry.WorkArea;
        main_bounds=[TintFableMarketing.Frame]::Rect($Ui.main);target_bounds=$geometry.Window;desktop=$geometry.Desktop;work_area=$geometry.WorkArea;dpi=$geometry.Dpi}
}
function Invoke-TintFrameCapture($Operations,[int]$ProcessId,[long]$Main,[long]$Target,[string]$MainTitle,[string]$TargetTitle){
    $before=& $Operations.Observe
    Assert-TintFrameSnapshot $before $ProcessId $Main $Target $MainTitle $TargetTitle
    [byte[]]$bytes=& $Operations.Capture $before.capture_bounds
    $after=& $Operations.Observe
    Assert-TintFrameSnapshot $after $ProcessId $Main $Target $MainTitle $TargetTitle
    if(($before|ConvertTo-Json -Depth 8 -Compress) -cne ($after|ConvertTo-Json -Depth 8 -Compress)){throw 'Native frame changed during screenshot'}
    if($bytes.Length -eq 0 -or $bytes.Length -gt 5000000){throw 'Native screenshot exceeds bound'}
    return @{before=$before;after=$after;bytes=$bytes}
}
function Save-TintCaptureFrame($Ui,$Scope,[string]$Stem,[string]$MainTitle){
    if($Stem -cnotin @('01-edited-canvas','02-export-recipe','03-exported-image')){throw 'Unknown product image slot'}
    Add-TintCaptureTypes
    $ops=@{Observe={Get-TintFrameSnapshot $Ui $Scope};Capture={param($bounds)
        $bitmap=[Drawing.Bitmap]::new($bounds[2],$bounds[3]);$graphics=[Drawing.Graphics]::FromImage($bitmap);$memory=[IO.MemoryStream]::new()
        try{$graphics.CopyFromScreen($bounds[0],$bounds[1],0,0,$bitmap.Size);$bitmap.Save($memory,[Drawing.Imaging.ImageFormat]::Png);return ,$memory.ToArray()}
        finally{$memory.Dispose();$graphics.Dispose();$bitmap.Dispose()}
    }}
    $frame=Invoke-TintFrameCapture $ops $Ui.process.Id $Ui.main $Scope.hwnd $MainTitle $Scope.title
    $path=Join-Path $Ui.output ($Stem+'.png');$file=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$file.Write($frame.bytes,0,$frame.bytes.Length);$file.Flush($true)}finally{$file.Dispose()}
    Write-NewUtf8Json (Join-Path $Ui.output ($Stem+'.json')) @{schema_version=1;purpose='unaltered native marketing screenshot';consumer_acceptance=$false;pixel_manipulation=$false;
        qualified_source_commit=$Ui.state.record.sourceCommit;package_full_name=$Ui.state.ownedPackageFullName;
        process_id=$Ui.process.Id;before=$frame.before;after=$frame.after;png=@{bytes=$frame.bytes.Length;sha256=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()};captured_at_utc=[DateTime]::UtcNow.ToString('o')}
}
function Invoke-TintCaptureLifecycle([Collections.IDictionary]$Operations) {
    $primary=$null;$cleanup=[Collections.Generic.List[string]]::new()
    try{foreach($name in @('Preflight','Prepare','Sign','Install','Activate','Workflow','Close','Uninstall')){& $Operations[$name]|Out-Host}}catch{$primary=$_.Exception.Message;try{& $Operations.ObserveFailure|Out-Host}catch{$cleanup.Add('Failure observation: '+$_.Exception.Message)}}
    finally{foreach($name in @('Stop','RestoreDisplay','RemovePackage','RemoveProfileAndDemo','RemoveTrust','RemoveKey','RemoveTemporary')){try{& $Operations[$name]|Out-Host}catch{$cleanup.Add($name+': '+$_.Exception.Message)}}}
    return @{primary_error=$primary;cleanup_errors=@($cleanup)}
}

function Save-TintCaptureFailure($State){
    if(-not $State.ui -or -not $State.processOwned -or $State.process.HasExited){return}
    $ui=$State.ui;$scopes=@(Get-PixelQuayScopes $ui)
    $ui.record.failure_windows=@($scopes|ForEach-Object {@{hwnd=$_.hwnd;pid=$_.process.Id;title=$_.title;class=$_.class}})
    $foreground=@($scopes|Where-Object hwnd -EQ ([PixelQuayQualification.ConsumerNative]::ForegroundWindow()))
    if($foreground.Count -ne 1){throw 'No exact owned foreground failure surface'}
    $scope=$foreground[0];Assert-PixelQuayScope $ui $scope
    Save-PixelQuayObservation $ui $scope 'failure'
    $root=[Windows.Automation.AutomationElement]::FromHandle([IntPtr]$scope.hwnd)
    if($root.Current.ProcessId -ne $scope.process.Id -or $root.Current.NativeWindowHandle -ne $scope.hwnd){throw 'Failure UIA root differs from exact owned window'}
    $nodes=$root.FindAll([Windows.Automation.TreeScope]::Subtree,[Windows.Automation.Condition]::TrueCondition)
    $ui.record.failure_accessibility=@(for($i=0;$i -lt [Math]::Min($nodes.Count,512);$i++){
        try{$c=$nodes.Item($i).Current;@{name=$c.Name;type=$c.ControlType.ProgrammaticName;automation_id=$c.AutomationId;pid=$c.ProcessId;enabled=$c.IsEnabled;offscreen=$c.IsOffscreen}}catch{@{index=$i;error=$_.Exception.Message}}
    });$ui.record.failure_accessibility_truncated=$nodes.Count -gt 512
}

function Assert-TintCaptureFrames($State){
    foreach($stem in @('01-edited-canvas','02-export-recipe','03-exported-image')){
        $row=Get-Content -LiteralPath (Join-Path $State.output ($stem+'.json')) -Raw|ConvertFrom-Json -AsHashtable
        $mainTitle=if($stem -ceq '03-exported-image'){'Cedar Coast-newsletter.png - TintFable'}else{'Cedar Coast.png - TintFable'}
        $targetTitle=if($stem -ceq '02-export-recipe'){'Export with Recipe'}else{$mainTitle}
        if($row.schema_version -ne 1 -or $row.pixel_manipulation -ne $false -or $row.consumer_acceptance -ne $false -or $row.process_id -ne $State.process.Id -or
           $row.qualified_source_commit -cne $State.record.sourceCommit -or $row.package_full_name -cne $State.ownedPackageFullName){throw 'Retained screenshot source/process/package differs'}
        foreach($snapshot in @($row.before,$row.after)){Assert-TintFrameSnapshot $snapshot $State.process.Id $State.ui.main $row.before.target $mainTitle $targetTitle}
        if(($row.before|ConvertTo-Json -Depth 8 -Compress) -cne ($row.after|ConvertTo-Json -Depth 8 -Compress)){throw 'Retained screenshot before/after observation differs'}
        $null=Assert-FileMatchesRecord (Join-Path $State.output ($stem+'.png')) ([pscustomobject]$row.png) 'Unaltered native screenshot'
    }
    $State.framesVerified=$true
}
