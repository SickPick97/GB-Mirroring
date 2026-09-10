$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$folder=Join-Path $root ('dist/pico-reports/'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$null=New-Item -ItemType Directory -Force $folder
$port=$null
$results=@()
$report=@{status='INCOMPLETE'; phases=@(); error=$null; scope='Pico-local multiplayer validation; no image or cartridge capture'}
$writer=New-Object System.IO.StreamWriter((Join-Path $folder 'usb.jsonl'),$false,[System.Text.Encoding]::UTF8)
try {
 $devices=@(Get-PnpDevice -PresentOnly | Where-Object {$_.InstanceId -match 'VID_CAFE&PID_4022' -and $_.FriendlyName -match '\(COM\d+\)'})
 if($devices.Count -ne 1){throw 'Serve un solo Pico con firmware Multi Profile 0.3.7.'}
 $null=$devices[0].FriendlyName -match '\((COM\d+)\)'
 $port=New-Object System.IO.Ports.SerialPort($Matches[1],115200)
 $port.DtrEnable=$true;$port.WriteTimeout=2000;$port.Open()
 Start-Sleep -Milliseconds 400
 $port.DiscardInBuffer();$port.WriteLine('START')
 $start=Get-Date;$notice=Get-Date;$partial='';$finished=$false
 while(!$finished){
  if(((Get-Date)-$start).TotalSeconds -gt 190){throw 'Timeout: conservare usb.jsonl e rapporto.json.'}
  if(((Get-Date)-$notice).TotalSeconds -ge 5){Write-Host 'Misura sul Pico in corso; attendere il riepilogo...';$notice=Get-Date}
  $partial+=$port.ReadExisting()
  if($partial.Length -gt 8192){throw 'Risposta USB troppo lunga'}
  while($partial.Contains("`n")){
   $i=$partial.IndexOf("`n");$line=$partial.Substring(0,$i).Trim();$partial=$partial.Substring($i+1)
   if(!$line){continue}
   $writer.WriteLine($line);$writer.Flush();$item=$line|ConvertFrom-Json
   switch($item.event){
    'begin' {if($item.firmware -ne '0.3.7'){throw 'Versione firmware inattesa'};Write-Host 'Pico avviato: scansione 5 x 20 secondi e conferma 60 secondi.'}
    'result' {
     $speed=0
     if($item.packet_span_us -gt 0){$speed=[math]::Round($item.verified_payload_bytes*1000000.0/$item.packet_span_us,1)}
     $item|Add-Member -NotePropertyName verified_payload_bytes_s -NotePropertyValue $speed
     $results+= $item
     Write-Host "Timing $($item.timing): $speed B/s; clean=$($item.clean); parole=$($item.words)"
    }
    'done' {
     $finished=$true
     $scan=@($results | Where-Object {!$_.confirmation})
     $confirm=@($results | Where-Object {$_.confirmation})
     $validScan=($scan.Count -eq 5 -and (($scan.timing -join ',') -eq '125,60,30,10,1') -and @($scan | Where-Object {!$_.clean -or $_.requested_seconds -ne 20}).Count -eq 0)
     $validConfirm=($confirm.Count -eq 1 -and $confirm[0].clean -and $confirm[0].requested_seconds -eq 60 -and @($scan | Where-Object {$_.clean -and $_.timing -eq $confirm[0].timing}).Count -gt 0)
     if($item.clean -and $validScan -and $validConfirm){$report.status='PASS'}elseif($validConfirm){$report.status='PARTIAL'}else{$report.status='FAILED'}
    }
    default {throw 'Evento USB sconosciuto'}
   }
  }
  Start-Sleep -Milliseconds 20
 }
}catch{$report.error=$_.Exception.Message;Write-Host "ERRORE: $($report.error)"}
finally{
 if($null -ne $port){if($port.IsOpen){$port.Close()};$port.Dispose()}
 $writer.Dispose();$report.phases=$results
 $report|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $folder 'rapporto.json')
}
Write-Host "Esito: $($report.status). Invia rapporto.json e usb.jsonl da $folder"
Write-Host 'Puoi spegnere il GBA. Questa prova non produce immagini.'
if($report.status -ne 'PASS'){exit 1}
