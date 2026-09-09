param([ValidateRange(1,32)][int]$Jobs = 4)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$projectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Comando fallito: $Program (uscita $LASTEXITCODE)" }
}

Push-Location $projectRoot
try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $cmakePath = (Get-Command cmake -ErrorAction Stop).Source
    $null = Get-Command arm-none-eabi-gcc -ErrorAction Stop
    Invoke-Checked -Program $pythonPath -Arguments @('tools/prepare_dependencies.py')
    $ninjaPath = (Join-Path $projectRoot 'tools/ninja/ninja.exe').Replace('\','/')
    Invoke-Checked -Program $cmakePath -Arguments @('-S','.', '-B','build/uvc-test','-G','Ninja',
        "-DCMAKE_MAKE_PROGRAM=$ninjaPath",'-DCMAKE_BUILD_TYPE=Release')
    Invoke-Checked -Program $cmakePath -Arguments @('--build','build/uvc-test','--parallel',"$Jobs")
    New-Item -ItemType Directory -Force dist | Out-Null
    Invoke-Checked -Program $pythonPath -Arguments @('tools/make_uf2.py',
        'build/uvc-test/gbmirroring_uvc_test.bin','dist/gbmirroring-uvc-test-v0.1.0.uf2')
    Invoke-Checked -Program $pythonPath -Arguments @('tools/verify_firmware.py')
    Write-Host 'Pronto: dist/gbmirroring-uvc-test-v0.1.0.uf2. Nessun dispositivo e stato programmato.'
} finally { Pop-Location }

