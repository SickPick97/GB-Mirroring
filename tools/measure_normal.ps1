$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$folder = Join-Path $root ('dist/normal-reports/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$null = New-Item -ItemType Directory -Force $folder
$port = $null
$writer = New-Object System.IO.StreamWriter((Join-Path $folder 'usb.jsonl'), $false, [System.Text.Encoding]::UTF8)
$status = @{ completed = $false; error = $null; port = $null }
try {
    $devices = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_CAFE&PID_4021' -and $_.FriendlyName -match '\(COM\d+\)' })
    if ($devices.Count -ne 1) { throw 'Serve un solo Pico con firmware GBMirroring Normal Test. Carica il nuovo UF2 e riprova.' }
    $null = $devices[0].FriendlyName -match '\((COM\d+)\)'
    $portName = $Matches[1]
    $status.port = $portName
    $status.device = $devices[0].InstanceId
    $port = New-Object System.IO.Ports.SerialPort($portName,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
    $port.ReadTimeout = 1000
    $port.WriteTimeout = 1000
    $port.ReadBufferSize = 65536
    $port.DtrEnable = $true
    $port.NewLine = "`n"
    $port.Open()
    Start-Sleep -Milliseconds 400
    $port.DiscardInBuffer()
    $port.WriteLine('START')
    $lastActivity = Get-Date
    $deadlineSeconds = 15
    $done = 0
    $lastClean = $false
    $imageBlocks = 0
    $partial = ''
    while ($done -lt 2) {
        # ReadExisting preserves partial lines across polling timeouts.
        $incoming = $port.ReadExisting()
        if (((Get-Date) - $lastActivity).TotalSeconds -gt $deadlineSeconds) { throw 'Timeout: nessun pacchetto valido in progresso. Conserva il rapporto diagnostico.' }
        if ($incoming.Length -eq 0) {
            if (((Get-Date) - $lastActivity).TotalSeconds -gt $deadlineSeconds) { throw 'Timeout: nessun progresso. Conserva il rapporto e controlla le istruzioni sul GBA.' }
            Start-Sleep -Milliseconds 20
            continue
        }
        $partial += $incoming
        if ($partial.Length -gt 131072) { throw 'Flusso seriale senza delimitatori validi.' }
        while ($partial.Contains("`n")) {
            $split = $partial.IndexOf("`n")
            $line = $partial.Substring(0,$split).Trim()
            $partial = $partial.Substring($split+1)
            if (!$line) { continue }
            $writer.WriteLine($line)
            $writer.Flush()
            $item = $line | ConvertFrom-Json
            # Heartbeats prove USB is alive, but must not extend the packet timeout.
            if ($item.event -ne 'diagnostic') { $lastActivity = Get-Date }
            switch ($item.event) {
                'diagnostic' { Write-Host "Diagnostica: parole=$($item.words), pacchetti validi=$($item.valid_headers), CRC errati=$($item.crc_errors), pin=$($item.pins), PIO=$($item.pio_pc)" }
                'ready' { Write-Host 'PRONTO. Premi e rilascia A sul GBA per il test 256 kHz.'; $deadlineSeconds=180 }
                'begin' { Write-Host "Ricezione iniziata: clock $($item.rate) Hz."; $deadlineSeconds=20; $imageBlocks=0 }
                'progress' { Write-Host "Pacchetti verificati: $($item.packets)/1024" }
                'result' { $lastClean=[bool]$item.clean; Write-Host "Esito del canale: clean=$lastClean. Ricevo la schermata..." }
                'image' { $imageBlocks++ }
                'error' { Write-Host "Errore firmware: $($item.message)" }
                'phase_done' {
                    $done++
                    if (!$lastClean) { throw 'La fase non e pulita. Non avviare la velocita successiva; analizzeremo i risultati.' }
                    if ($imageBlocks -ne 300) { throw 'Screenshot USB incompleto. Non avviare la velocita successiva.' }
                    if ($done -eq 1) { Write-Host '256 kHz completato. Ora premi e rilascia B sul GBA per provare 2 MHz.'; $deadlineSeconds=180 }
                }
                default { throw "Evento USB sconosciuto: $($item.event)" }
            }
        }
    }
    $status.completed=$true
} catch {
    $status.error=$_.Exception.Message
    Write-Host "ERRORE: $($status.error)"
} finally {
    if ($null -ne $port) { if ($port.IsOpen) { $port.Close() }; $port.Dispose() }
    $writer.Dispose()
    $status | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $folder 'host.json')
}
& (Join-Path $root 'runtime/python/python.exe') (Join-Path $root 'tools/normal_report.py') $folder
Write-Host "Risultati: $folder"
Write-Host 'Puoi spegnere il GBA. Inviami questa cartella di risultati.'
if (!$status.completed -or $LASTEXITCODE -ne 0) { exit 1 }
