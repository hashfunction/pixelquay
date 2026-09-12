# Copyright 2026 Trieflow LLC. MIT licensed. External normal-consumer UI driver.
function Invoke-PixelQuayFiles([string]$Operation, [string]$StatePath, [string[]]$Extra=@(), [string]$Python='python') {
    $arguments=@((Join-Path $PSScriptRoot 'consumer_workflow.py'),$Operation,'--state',$StatePath)+$Extra
    $result=& $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw "Independent consumer file check failed: $Operation" }
    ($result -join "`n") | ConvertFrom-Json -AsHashtable
}
function Wait-PixelQuayConsumer([scriptblock]$Observe, [string]$Label) {
    $deadline=[DateTime]::UtcNow.AddSeconds(30); $last='No matching observation'
    do {
        try { $value=& $Observe; if ($null -ne $value -and $value -ne $false) { return $value } }
        catch { $last=$_.Exception.Message }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Consumer wait failed (${Label}): $last"
}
function Assert-PixelQuayScope($Ui, $Scope, [bool]$Foreground=$true) {
    [PixelQuayQualification.ConsumerNative]::Require($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Foreground)
}
function Get-PixelQuayScopes($Ui) {
    if ($Ui.process.HasExited -or $Ui.process.SafeHandle.IsClosed -or [PixelQuayQualification.ConsumerNative]::Pid($Ui.main) -ne $Ui.process.Id) { throw 'Retained broker process/main-window ownership changed' }
    foreach ($hwnd in [PixelQuayQualification.ConsumerNative]::Windows($Ui.main)) {
        $owner=[PixelQuayQualification.ConsumerNative]::Pid($hwnd)
        $process=$Ui.process
        if ($owner -ne $Ui.process.Id) {
            if (-not $Ui.brokers.ContainsKey([string]$owner)) {
                if ($Ui.brokers.Count -ge 8) { throw 'Picker handle budget exceeded' }
                $candidate=[Diagnostics.Process]::GetProcessById($owner)
                try {
                    $handle=$candidate.SafeHandle
                    if ($handle.IsInvalid -or $handle.IsClosed -or $candidate.HasExited -or
                        [PixelQuayQualification.ConsumerNative]::Pid($hwnd) -ne $owner -or
                        $Ui.main -notin [PixelQuayQualification.ConsumerNative]::Owners($hwnd)) { throw 'Picker identity changed while retaining its handle' }
                    $Ui.brokers[[string]$owner]=$candidate
                } catch { $candidate.Dispose(); throw }
            }
            $process=$Ui.brokers[[string]$owner]
        }
        $scope=@{process=$process; hwnd=[long]$hwnd; title=[PixelQuayQualification.ConsumerNative]::Title($hwnd)}
        # Read names only after native ownership is known. Disabled parent
        # windows remain observable but cannot be selected as input targets.
        $scope.class=[PixelQuayQualification.ConsumerNative]::Class($hwnd)
        $scope
    }
}
function Get-PixelQuayScope($Ui,[string]$Title,[switch]$Main,[switch]$Picker,[switch]$Completion) {
    $matches=@(Get-PixelQuayScopes $Ui | Where-Object {
        if ($Main) { $_.hwnd -eq $Ui.main -and $_.title -ceq $Title }
        elseif ($Completion) { $_.hwnd -ne $Ui.main -and $_.process.Id -eq $Ui.process.Id -and $_.title -cne 'Exporting image' }
        else { $_.hwnd -ne $Ui.main -and $_.title -ceq $Title -and (-not $Picker -or $_.class -ceq '#32770') }
    })
    if ($matches.Count -ne 1) { return $null }
    Assert-PixelQuayScope $Ui $matches[0] $false
    [PixelQuayQualification.ConsumerNative]::Foreground($Ui.process,$Ui.main,$matches[0].process,$matches[0].hwnd,$matches[0].title)
    $matches[0]
}
function Send-PixelQuayKeys($Ui,$Scope,[int[]]$Keys) {
    Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::Chord($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Keys)
}
function Send-PixelQuayText($Ui,$Scope,[string]$Text) {
    Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::Text($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Text)
}
function Send-PixelQuayFileNameKeys($Ui,$Scope,[long]$Focus,[int[]]$Keys) {
    Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::FileNameChord($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus,$Keys)
}
function Send-PixelQuayFileNameText($Ui,$Scope,[long]$Focus,[string]$Text) {
    Assert-PixelQuayScope $Ui $Scope
    [PixelQuayQualification.ConsumerNative]::FileNameTextInput($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title,$Focus,$Text)
}
function Get-PixelQuayPickerControl($Ui,$Scope,[string]$Id,[string]$Type,[string[]]$Names=@()) {
    Assert-PixelQuayScope $Ui $Scope
    $root=[Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Scope.hwnd)
    if ($root.Current.NativeWindowHandle -ne $Scope.hwnd -or $root.Current.ProcessId -ne $Scope.process.Id) { throw 'Picker UIA root differs from owned HWND' }
    $all=$root.FindAll([Windows.Automation.TreeScope]::Subtree,[Windows.Automation.Condition]::TrueCondition)
    if ($all.Count -gt 512) { throw 'Picker UIA tree exceeded bound' }
    if ($Ui.ContainsKey('record')) {
        $nodes=@(for($index=0;$index -lt $all.Count;$index++){
            $node=$all.Item($index).Current
            @{name=$node.Name;automation_id=$node.AutomationId;type=$node.ControlType.ProgrammaticName;pid=$node.ProcessId;enabled=$node.IsEnabled;offscreen=$node.IsOffscreen}
        })
        $Ui.record.picker_trees.Add(@{dialog=$Scope.title;hwnd=$Scope.hwnd;pid=$Scope.process.Id;requested_id=$Id;requested_names=$Names;requested_type=$Type;nodes=$nodes})
    }
    $matches=@(for ($i=0;$i -lt $all.Count;$i++) {
        $element=$all.Item($i); $c=$element.Current
        $identified=if($Names.Count){$c.Name -cin $Names}else{$c.AutomationId -ceq $Id}
        if ($identified -and $c.ControlType.ProgrammaticName -ceq "ControlType.$Type" -and $c.IsEnabled -and -not $c.IsOffscreen -and $c.ProcessId -eq $Scope.process.Id) { $element }
    })
    if ($matches.Count -ne 1) { throw "Native picker control is missing or ambiguous: $Id/$Type" }
    $matches[0]
}
function Assert-PixelQuayPickerElement($Ui,$Scope,$Element) {
    Assert-PixelQuayScope $Ui $Scope
    $current=$Element.Current
    if ($current.ProcessId -ne $Scope.process.Id -or -not $current.IsEnabled -or $current.IsOffscreen) { throw 'Picker control identity or visibility changed' }
    $ancestor=$Element
    for ($i=0;$i -lt 32 -and $null -ne $ancestor;$i++) {
        if ($ancestor.Current.NativeWindowHandle -eq $Scope.hwnd -and $ancestor.Current.ProcessId -eq $Scope.process.Id) { return }
        $ancestor=[Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($ancestor)
    }
    throw 'Picker control no longer descends from the exact owned dialog'
}
function Save-PixelQuayFileNameFailure($Ui,$Scope,[long]$ExpectedFocus,[string]$Stage,[Exception]$Exception) {
    if(-not $Ui.record.Contains('picker_failures')){$Ui.record.picker_failures=[Collections.Generic.List[object]]::new()}
    if($Ui.record.picker_failures.Count -ge 16){throw 'Native picker failure evidence exceeded bound'}
    $native=$null;$error=$Exception
    # PowerShell wraps static C# exceptions. Retain the exact evidence attached
    # at the refusing native boundary, without making fresh input or UI queries.
    for($i=0;$i -lt 8 -and $null -ne $error;$i++){
        if($error.Data.Contains('PixelQuay.FileNameEvidence')){$native=$error.Data['PixelQuay.FileNameEvidence'];break}
        $error=$error.InnerException
    }
    $message=$Exception.Message
    if($message.Length -gt 4096){$message=$message.Substring(0,4096)}
    $Ui.record.picker_failures.Add(@{stage=$Stage;title=$Scope.title;hwnd=$Scope.hwnd;pid=$Scope.process.Id;
        expected_focus=$ExpectedFocus;native=$native;error=$message;observed_utc=[DateTime]::UtcNow.ToString('o')})
}
function Set-PixelQuayPickerPath($Ui,[string]$Title,[string]$Path) {
    $scope=Wait-PixelQuayConsumer { Get-PixelQuayScope $Ui $Title -Picker } "owned native picker $Title"
    $focus=0;$stage='filename-mnemonic'
    try {
        # Run34675708778 exposes Win32 filename/buttons as UIA Pane without their
        # edit/invoke providers. Use normal filename mnemonic/input with native
        # focused Edit ancestry, read-only state and exact text readback instead.
        Send-PixelQuayKeys $Ui $scope @(18,78)
        $stage='observe-after-alt-n'
        $filename=[PixelQuayQualification.ConsumerNative]::FileName($Ui.process,$Ui.main,$scope.process,$scope.hwnd,$scope.title,0)
        $focus=$filename.Focus
        $Ui.record.picker_fields.Add(@{dialog=$scope.title;hwnd=$scope.hwnd;pid=$scope.process.Id;focus=$focus;class=$filename.Class;filename_control_id_verified=$filename.HasFileNameId;native=$filename;input='native Alt+N, Ctrl+A, Unicode text, Enter';readback='bounded WM_GETTEXT'})
        $stage='select-filename'
        Send-PixelQuayFileNameKeys $Ui $scope $focus @(17,65)
        $stage='observe-before-text'
        $null=[PixelQuayQualification.ConsumerNative]::FileName($Ui.process,$Ui.main,$scope.process,$scope.hwnd,$scope.title,$focus)
        $stage='type-filename'
        Send-PixelQuayFileNameText $Ui $scope $focus ($Path.Replace('/','\'))
        $stage='readback-filename'
        $actual=[PixelQuayQualification.ConsumerNative]::FileNameText($Ui.process,$Ui.main,$scope.process,$scope.hwnd,$scope.title,$focus)
        if ($actual -cne $Path.Replace('/','\')) { throw 'Native picker did not retain exact local path text' }
        $stage='capture-picker'
        Save-PixelQuayObservation $Ui $scope ('picker-'+$Ui.record.observations.Count)
        $stage='observe-before-enter'
        $null=[PixelQuayQualification.ConsumerNative]::FileName($Ui.process,$Ui.main,$scope.process,$scope.hwnd,$scope.title,$focus)
        $stage='submit-filename'
        Send-PixelQuayFileNameKeys $Ui $scope $focus @(13)
        $stage='picker-disappearance'
        Wait-PixelQuayConsumer { $scope.hwnd -notin [PixelQuayQualification.ConsumerNative]::Windows($Ui.main) } 'native picker disappearance' | Out-Null
    } catch {
        $primary=$_
        try { Save-PixelQuayFileNameFailure $Ui $scope $focus $stage $primary.Exception }
        catch { $Ui.record.picker_failure_evidence_error=$_.Exception.Message }
        throw $primary
    }
}
function Get-PixelQuayGeometry($Ui,$Scope,[string]$Stage) {
    Assert-PixelQuayScope $Ui $Scope
    if ($Ui.record.geometry.Count -ge 64) { throw 'Owned geometry evidence exceeded bound' }
    $geometry=[PixelQuayQualification.ConsumerNative]::Geometry($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title)
    $Ui.record.geometry.Add(@{stage=$Stage;hwnd=$Scope.hwnd;pid=$Scope.process.Id;title=$Scope.title;
        window=$geometry.Window;desktop=$geometry.Desktop;work_area=$geometry.WorkArea;dpi=$geometry.Dpi})
    return $geometry
}
function Set-PixelQuayMainPlacement($Ui,$Scope) {
    $null=Get-PixelQuayGeometry $Ui $Scope 'before-placement'
    [PixelQuayQualification.ConsumerNative]::Place($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title)
    Wait-PixelQuayConsumer {
        $geometry=[PixelQuayQualification.ConsumerNative]::Geometry($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title)
        $null=[PixelQuayQualification.ConsumerNative]::PlacedBounds($geometry)
        return $true
    } 'actual readable owned window placement' | Out-Null
    $null=Get-PixelQuayGeometry $Ui $Scope 'after-placement'
}
function Save-PixelQuayObservation($Ui,$Scope,[string]$Stage) {
    Assert-PixelQuayScope $Ui $Scope
    $geometry=Get-PixelQuayGeometry $Ui $Scope $Stage
    $before=[PixelQuayQualification.ConsumerNative]::VisibleBounds($geometry)
    $bitmap=[Drawing.Bitmap]::new($before[2],$before[3]); $graphics=[Drawing.Graphics]::FromImage($bitmap)
    $stream=[IO.MemoryStream]::new()
    try {
        $graphics.CopyFromScreen($before[0],$before[1],0,0,$bitmap.Size)
        $after=[PixelQuayQualification.ConsumerNative]::Bounds($Ui.process,$Ui.main,$Scope.process,$Scope.hwnd,$Scope.title)
        if (($before -join ',') -cne ($after -join ',')) { throw 'Owned window or desktop moved during screenshot' }
        $bitmap.Save($stream,[Drawing.Imaging.ImageFormat]::Png)
        if ($stream.Length -gt 2MB) { throw 'Consumer screenshot exceeds bound' }
        $path=Join-Path $Ui.output ("consumer-$Stage.png")
        $file=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $stream.Position=0; $stream.CopyTo($file) } finally { $file.Dispose() }
        $observation=@{stage=$Stage;hwnd=$Scope.hwnd;pid=$Scope.process.Id;title=$Scope.title;class=$Scope.class;owner_chain=[PixelQuayQualification.ConsumerNative]::Owners($Scope.hwnd);bounds=$before;screenshot=[IO.Path]::GetFileName($path);sha256=(Get-FileHash $path).Hash.ToLowerInvariant()}
        $Ui.record.observations.Add($observation)
    } finally { $stream.Dispose(); $graphics.Dispose(); $bitmap.Dispose() }
}
function Get-PixelQuayMain($Ui,[string]$Title) {
    Wait-PixelQuayConsumer { Get-PixelQuayScope $Ui $Title -Main } "exact document title $Title"
}
function Open-PixelQuayImage($Ui,[string]$Current,[string]$Path,[string]$Expected) {
    $main=Get-PixelQuayMain $Ui $Current
    Send-PixelQuayKeys $Ui $main @(17,79)
    Set-PixelQuayPickerPath $Ui 'Open Image File' $Path
    Get-PixelQuayMain $Ui $Expected
}
function Save-PixelQuayImage($Ui,[string]$Current,[string]$Path,[string]$Expected) {
    $main=Get-PixelQuayMain $Ui $Current
    Send-PixelQuayKeys $Ui $main @(17,16,83)
    Set-PixelQuayPickerPath $Ui 'Save Image File' $Path
    Get-PixelQuayMain $Ui $Expected
}
function Set-PixelQuayRecipeField($Ui,$Scope,[int]$Mnemonic,[string]$Text) {
    Send-PixelQuayKeys $Ui $Scope @(18,$Mnemonic)
    Send-PixelQuayKeys $Ui $Scope @(17,65)
    Send-PixelQuayText $Ui $Scope $Text
}
function Invoke-PixelQuayConsumerWorkflow([Diagnostics.Process]$Process,[string]$StatePath,[string]$Output,[Collections.IDictionary]$DisplayState) {
    if (-not ('PixelQuayQualification.ConsumerNative' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'consumer_native.cs') }
    Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Drawing
    $fixture=Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json -AsHashtable
    $Process.Refresh(); $retained=$Process.SafeHandle
    if ($retained.IsClosed -or $retained.IsInvalid -or $Process.HasExited) { throw 'Broker lifetime is unavailable' }
    $ui=@{process=$Process;main=[long]$Process.MainWindowHandle;brokers=@{};output=$Output;
        record=@{schema='pixelquay-consumer-workflow-v1';process_id=$Process.Id;phase='normal-consumer-ui-actions';geometry=[Collections.Generic.List[object]]::new();picker_fields=[Collections.Generic.List[object]]::new();picker_trees=[Collections.Generic.List[object]]::new();observations=[Collections.Generic.List[object]]::new()}}
    try {
        $main=Get-PixelQuayMain $ui 'Unsaved Image 1 - TintFable'
        $null=Get-PixelQuayGeometry $ui $main 'before-display-preparation'
        if ($null -eq $DisplayState) { throw 'Retained outer display restoration state is required' }
        Start-PixelQuayConsumerDisplay $DisplayState
        # The outer qualification owner restores the retained original mode
        # after its normal-close/owned-process cleanup, including failures.
        $main=Get-PixelQuayMain $ui 'Unsaved Image 1 - TintFable'
        Set-PixelQuayMainPlacement $ui $main
        $main=Open-PixelQuayImage $ui $main.title (Join-Path $fixture.root 'source.png') 'source.png - TintFable'
        Save-PixelQuayObservation $ui $main 'opened'
        Send-PixelQuayKeys $ui $main @(17,72)
        $main=Get-PixelQuayMain $ui 'source.png* - TintFable'
        Save-PixelQuayObservation $ui $main 'rotated'
        $main=Save-PixelQuayImage $ui $main.title (Join-Path $fixture.root 'edited.png') 'edited.png - TintFable'
        $ui.record.edited=Invoke-PixelQuayFiles edited $StatePath
        Send-PixelQuayKeys $ui $main @(17,18,69)
        $recipe=Wait-PixelQuayConsumer { Get-PixelQuayScope $ui 'Export with Recipe' } 'recipe dialog'
        Set-PixelQuayRecipeField $ui $recipe 78 'Consumer proof 32x48'
        Set-PixelQuayRecipeField $ui $recipe 87 '32'
        Set-PixelQuayRecipeField $ui $recipe 72 '48'
        Set-PixelQuayRecipeField $ui $recipe 83 '-proof'
        # From the mnemonic-bound suffix: replacement checkbox, Save recipe.
        Send-PixelQuayKeys $ui $recipe @(9); Send-PixelQuayKeys $ui $recipe @(9)
        Send-PixelQuayKeys $ui $recipe @(32)
        Save-PixelQuayObservation $ui $recipe 'recipe-saved'
        Send-PixelQuayKeys $ui $recipe @(27)
        $main=Get-PixelQuayMain $ui 'edited.png - TintFable'
        Send-PixelQuayKeys $ui $main @(17,18,69)
        $recipe=Wait-PixelQuayConsumer { Get-PixelQuayScope $ui 'Export with Recipe' } 'saved recipe reloaded in a new dialog'
        Save-PixelQuayObservation $ui $recipe 'recipe-reloaded'
        Send-PixelQuayKeys $ui $recipe @(18,83)
        # Suffix -> replacement checkbox -> Save recipe -> destination folder.
        foreach ($i in 1..3) { Send-PixelQuayKeys $ui $recipe @(9) }
        Send-PixelQuayKeys $ui $recipe @(32)
        Set-PixelQuayPickerPath $ui 'Export destination' $fixture.root
        $recipe=Wait-PixelQuayConsumer { Get-PixelQuayScope $ui 'Export with Recipe' } 'recipe destination accepted'
        Save-PixelQuayObservation $ui $recipe 'export-plan'
        Send-PixelQuayKeys $ui $recipe @(18,69)
        Wait-PixelQuayConsumer { Test-Path -LiteralPath (Join-Path $fixture.root 'edited-proof.png') -PathType Leaf } 'exported image publication' | Out-Null
        $ui.record.exported=Invoke-PixelQuayFiles exported $StatePath
        $completion=Wait-PixelQuayConsumer { Get-PixelQuayScope $ui '' -Completion } 'owned export completion dialog'
        Save-PixelQuayObservation $ui $completion 'export-completed'
        Send-PixelQuayKeys $ui $completion @(13)
        $main=Get-PixelQuayMain $ui 'edited.png - TintFable'
        $main=Open-PixelQuayImage $ui $main.title (Join-Path $fixture.root 'edited-proof.png') 'edited-proof.png - TintFable'
        Save-PixelQuayObservation $ui $main 'reopened'
        Send-PixelQuayKeys $ui $main @(17,72)
        $main=Save-PixelQuayImage $ui 'edited-proof.png* - TintFable' (Join-Path $fixture.root 'reopened.png') 'reopened.png - TintFable'
        $ui.record.reopened=Invoke-PixelQuayFiles reopened $StatePath
        Save-PixelQuayObservation $ui $main 'reopened-witness'
        $ui.record.ui_actions_completed=$true
    } catch {
        $ui.record.error=$_.Exception.Message
        try {
            $owned=@(Get-PixelQuayScopes $ui)
            $ui.record.failure_windows=@($owned | ForEach-Object { @{hwnd=$_.hwnd;pid=$_.process.Id;title=$_.title;class=$_.class} })
            $foreground=@($owned | Where-Object hwnd -EQ ([PixelQuayQualification.ConsumerNative]::ForegroundWindow()))
            if ($foreground.Count -eq 1) { Save-PixelQuayObservation $ui $foreground[0] 'failure' }
        } catch { $ui.record.failure_observation_error=$_.Exception.Message }
        throw
    } finally {
        if ($null -ne $DisplayState) { $ui.record.native_display=$DisplayState.displayEvidence }
        foreach ($broker in $ui.brokers.Values) { $broker.Dispose() }
        try { Write-NewUtf8Json (Join-Path $Output 'consumer-workflow.json') $ui.record }
        catch {
            $primary=if($ui.record.ContainsKey('error')){$ui.record.error}else{'none'}
            throw "Consumer evidence write failed: $($_.Exception.Message). Primary: $primary"
        }
    }
    $ui.record
}
