$ErrorActionPreference='Stop'
$source=Get-Content (Join-Path $PSScriptRoot 'measure_pico.ps1') -Raw
$begin=$source.IndexOf('     $scan=@(')
$end=$source.IndexOf("`n    }",$begin)
$logic=[scriptblock]::Create($source.Substring($begin,$end-$begin))
function Phase($timing,$clean,$confirmation,$seconds){[pscustomobject]@{timing=$timing;clean=$clean;confirmation=$confirmation;requested_seconds=$seconds}}
$cases=@(
 @{rows=@((Phase 125 $true $false 20),(Phase 60 $true $false 20),(Phase 30 $true $false 20),(Phase 10 $true $false 20),(Phase 1 $true $false 20),(Phase 1 $true $true 60));done=$true;expected='PASS'},
 @{rows=@((Phase 125 $true $false 20),(Phase 60 $false $false 20),(Phase 125 $true $true 60));done=$false;expected='PARTIAL'},
 @{rows=@((Phase 125 $false $false 20));done=$false;expected='FAILED'},
 @{rows=@((Phase 125 $true $false 20),(Phase 125 $false $true 60));done=$false;expected='FAILED'}
)
foreach($case in $cases){
 $results=$case.rows;$item=[pscustomobject]@{clean=$case.done};$report=@{}
 . $logic
 if($report.status -ne $case.expected){throw "Expected $($case.expected), got $($report.status)"}
}
$errors=$null;$tokens=$null
$null=[System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'PowerShell syntax errors'}
Write-Host 'PASS: four scan outcome cases and PowerShell syntax.'
