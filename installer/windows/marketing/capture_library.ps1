# Copyright 2026 Trieflow LLC. MIT. Load original qualified production helpers.
param([Parameter(Mandatory)][string]$QualifiedSource)
$script:TintQualifiedSource=(Resolve-Path -LiteralPath $QualifiedSource).Path
. (Join-Path $script:TintQualifiedSource 'installer/windows/qualify-msix-install.ps1') -LibraryOnly -IdentityMode store
. (Join-Path $PSScriptRoot 'capture_helpers.ps1')
. (Join-Path $PSScriptRoot 'capture_ui.ps1')
. (Join-Path $PSScriptRoot 'capture_operations.ps1')
