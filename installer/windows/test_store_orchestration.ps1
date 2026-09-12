# Copyright 2026 Trieflow LLC. MIT. Replay the actual production package/install/export caller.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix.ps1') -LibraryOnly
$script:events=[Collections.Generic.List[object]]::new();$script:failure=0;$script:calls=0
function Invoke-Checked([string]$Program,[string[]]$Arguments) {
    $script:calls++;$script:events.Add(@{program=$Program;arguments=$Arguments})
    if($script:calls -eq $script:failure){throw 'original checked command failed'}
}
function Copy-Item {param($LiteralPath,$Destination,$ErrorAction) $script:events.Add(@{copy=$LiteralPath;destination=$Destination})}
foreach($failure in 0..5) {
    $script:failure=$failure;$script:calls=0;$script:events.Clear();$failed=$false
    try {Invoke-TintFablePackageRelease 'original-pwsh' ('a'*40) '/sdk' '/temporary' '/evidence'}catch{$failed=$_.Exception.Message -ceq 'original checked command failed'}
    if($failed -ne ($failure -ne 0) -or $script:calls -ne $(if($failure){$failure}else{5})){throw 'Original package/lifecycle failure did not stop subsequent actions'}
    $commands=@($script:events|Where-Object {$_.ContainsKey('arguments')})
    if($failure -eq 0) {
        $expected=@('installer/windows/msix_qualification.py','installer/windows/qualify-msix-install.ps1','installer/windows/msix_qualification.py','installer/windows/qualify-msix-install.ps1','installer/windows/store_export.py')
        for($index=0;$index -lt 5;$index++) {
            if($expected[$index] -cnotin $commands[$index].arguments){throw 'Original production sequence changed'}
            if($index -lt 4) {
                $mode=if($index -lt 2){'qualification'}else{'store'}
                $flag=if($index%2){'-IdentityMode'}else{'--identity-mode'}
                $arguments=$commands[$index].arguments
                if($arguments[[Array]::IndexOf($arguments,$flag)+1] -cne $mode){throw 'Production mode binding changed'}
                if($index%2 -and ($commands[$index].program -cne 'original-pwsh' -or '-File' -cnotin $arguments)){throw 'Installed lifecycle must use its original fresh PowerShell host'}
            }
        }
        if(@($script:events|Where-Object {$_.ContainsKey('copy')}).Count -ne 2){throw 'Both original package records must be retained'}
        $args=$commands[4].arguments
        if($args[[Array]::IndexOf($args,'--store-package')+1] -cnotmatch 'tintfable-msix-store-package[/\\]TintFable_1.0.1.0_x64.msix$'){throw 'Export did not receive the actual Store package'}
    }
}
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('tintfable-record-preservation-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($fixture)|Out-Null
try {
    $path=Join-Path $fixture 'msix-package-record.json';[IO.File]::WriteAllText($path,'preserve existing evidence')
    $script:failure=0;$script:calls=0;$script:events.Clear();$refused=$false
    try{Invoke-TintFablePackageRelease 'original-pwsh' ('a'*40) '/sdk' '/temporary' $fixture}catch{$refused=$_.Exception.Message -ceq 'Existing package evidence must not be replaced'}
    if(-not $refused -or $script:calls -ne 1 -or [IO.File]::ReadAllText($path) -cne 'preserve existing evidence'){throw 'Existing evidence was replaced or an installed action followed refusal'}
}finally{Remove-Item -LiteralPath $fixture -Recurse -Force}
Write-Output 'PASS: actual dual package/lifecycle/record/export sequence, five checked failure boundaries, and existing evidence preservation.'
