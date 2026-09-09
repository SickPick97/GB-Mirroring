$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$reportPath = Join-Path $projectRoot 'dist/diagnosi-usb.txt'
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('GBMirroring - diagnostica USB in sola lettura')
$lines.Add(('Data: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')))
$lines.Add(('Sistema: ' + [System.Environment]::OSVersion.VersionString))
$lines.Add('Atteso test: CAFE:4020 - GBMirroring - USB Test - servizio usbvideo')
$lines.Add('Normal test: CAFE:4021 - GBMirroring Normal Test - servizio usbser (porta COM)')
$lines.Add('Alternativi: 2FE3:000A = Celio; 2E8A:0003 = RP2040 in BOOTSEL')
$lines.Add('')
try {
    $devices = @(Get-PnpDevice -PresentOnly | Where-Object {
        $_.InstanceId -match 'VID_CAFE&PID_402[01]|VID_2FE3&PID_000A|VID_2E8A&PID_0003'
    })
    if ($devices.Count -eq 0) {
        $lines.Add('Nessuno degli identificativi previsto trovato fra i dispositivi presenti.')
    }
    foreach ($device in $devices) {
        $lines.Add(('Nome: ' + $device.FriendlyName))
        $lines.Add(('Stato: ' + $device.Status + '; classe: ' + $device.Class))
        $lines.Add(('ID: ' + $device.InstanceId))
        foreach ($key in @('DEVPKEY_Device_Service','DEVPKEY_Device_ProblemCode','DEVPKEY_Device_DriverVersion')) {
            try {
                $prop = Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName $key -ErrorAction Stop
                $lines.Add(($key + ': ' + ($prop.Data -join ', ')))
            } catch { $lines.Add(($key + ': non disponibile')) }
        }
        $lines.Add('')
    }
} catch {
    $lines.Add(('Lettura dispositivi non riuscita: ' + $_.Exception.Message))
}
$firmwarePath = Join-Path $projectRoot 'dist/gbmirroring-uvc-test-v0.1.0.uf2'
if (Test-Path -LiteralPath $firmwarePath) {
    $lines.Add(('SHA256 UF2 di test: ' + (Get-FileHash -LiteralPath $firmwarePath -Algorithm SHA256).Hash))
}
$lines.Add('Questo rapporto non verifica il video e non modifica driver o firmware.')
New-Item -ItemType Directory -Force (Split-Path -Parent $reportPath) | Out-Null
$lines | Set-Content -LiteralPath $reportPath -Encoding UTF8
$lines | ForEach-Object { Write-Host $_ }
Write-Host "Rapporto salvato in: $reportPath"
