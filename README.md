# GBMirroring

Progetto sperimentale per acquisire il video di un GBA/GBA SP attraverso un adattatore Link con Raspberry Pi Pico RP2040 e arrivare a una webcam USB autonoma, senza modificare internamente la console.

**Versione del pacchetto: 0.3.1. Prova corrente: normal mode 0.3.0.** Il video delle cartucce commerciali non e ancora implementato.

## Su un altro PC Windows

1. Accedi alla repository privata con il tuo account GitHub.
2. Scarica **Code → Download ZIP**, oppure clona la repository con GitHub Desktop.
3. Estrai tutto in una cartella scrivibile. Non avviare i BAT dentro lo ZIP.
4. Avvia **0-CONTROLLA-PC.bat**: verifica offline runtime e firmware, senza interrogare dispositivi.
5. Apri [PROVA-NORMAL.md](PROVA-NORMAL.md) e segui la procedura. I file principali sono **3-CARICA-NORMAL.bat** e **4-MISURA-NORMAL.bat**.

Il pacchetto contiene Python portatile, librerie USB, firmware UF2 e programmi multiboot compilati. Non serve l'intera cartella PROGETTO AMICO e non occorre installare strumenti di sviluppo per eseguire i test. Target attuale: Windows 10/11 x64, Pico RP2040 e GBA SP.

Su questo nuovo PC, se Celio non viene riconosciuto da PyUSB, conserva l'errore e usa CONTROLLA-USB.bat: la configurazione WinUSB del vecchio PC non viene trasferita dalla repository. I firmware UVC e Normal usano invece i driver USB standard di Windows. Non applicare un driver Celio al firmware Normal o UVC.

## Stato verificato

| Versione firmware | Risultato |
|---|---|
| UVC 0.1.0 | Immagine sintetica 240x160 a 10 FPS visualizzata in Fotocamera; riapertura verificata dall'utente. |
| Link 0.2.0 | Multiboot, cinque velocita senza errori; massimo 2623,9 B/s; cattura VRAM completa in 41,08 s. |
| Normal 0.3.0 | Compilazione e test software superati; prova fisica a 256 kHz/2 MHz ancora da fare. |

[Registro hardware](docs/VALIDAZIONE-HARDWARE.md) · [Storico modifiche](CHANGELOG.md) · [Piano](PIANO-GBMIRRORING.md).

## Aggiornamenti e risultati

Ogni modifica viene registrata con un commit; i pacchetti pronti hanno una versione e un tag. I firmware mantengono il loro numero specifico: il pacchetto 0.3.1 contiene gli stessi firmware del precedente test, con percorsi resi portatili.

Per aggiornare da un altro PC: usa **Fetch/Pull** in GitHub Desktop oppure scarica la nuova versione in una cartella distinta. Conserva le cartelle dei risultati prima di sostituire un'estrazione ZIP.

I nuovi risultati rimangono in dist/link-reports o dist/normal-reports, esclusi dai commit automatici per non caricare percorsi e identificativi locali. Dopo ogni test vengono analizzati, riassunti nel registro hardware e, quando utile, archiviati in forma ripulita in test-results. Non basta una modifica al codice per dichiarare superata una prova fisica.

## Contenuto

- firmware e tools: sorgenti e strumenti del progetto.
- dist: binari pronti e manifest di verifica.
- runtime/python: interprete portatile Windows e dipendenze USB preesistenti.
- vendor/celio_transport: i soli due moduli di trasporto/multiboot del pacchetto amico, invariati.
- docs e test-results: documentazione e risultati selezionati.

ROM commerciali, salvataggi, emulatori, materiale completo del progetto amico e dipendenze di compilazione scaricate non fanno parte della repository. Vedi [attribuzioni](THIRD_PARTY.md). La repository e destinata all'uso privato; nessuna nuova licenza viene applicata ai componenti di terzi.
