# GBMirroring

Progetto sperimentale per acquisire il video di un GBA/GBA SP attraverso un adattatore Link con Raspberry Pi Pico RP2040 e arrivare a una webcam USB autonoma, senza modificare internamente la console.

**Versione pacchetto 0.7.1. [Prova integrata Smeraldo](PROVA-SMERALDO.md).** Correzione delle pause osservate nella 0.7.0: recupero CRC degli errori singoli, richieste di ripristino senza ripetizioni dopo il recupero, cache conservata fra transizioni completate. Pico 0.7.0 invariato: chi lo ha gia installato non deve rifare il flash. Correzioni verificate in software; risultato hardware da confermare. UVC autonoma non inclusa.

## Su un altro PC Windows

1. Accedi alla repository privata con il tuo account GitHub.
2. Scarica **Code → Download ZIP**, oppure clona la repository con GitHub Desktop.
3. Estrai tutto in una cartella scrivibile. Non avviare i BAT dentro lo ZIP.
4. Segui la preparazione in **PROVA-SMERALDO.md** e installa il firmware unificato una sola volta.
5. Avvia **14-AVVIA-SMERALDO.bat**: controllo dei file, multiboot e anteprima nello stesso programma. Il banco homebrew resta disponibile con gli avvii 10/11.

Il pacchetto contiene Python portatile, librerie USB, firmware UF2 e programmi multiboot compilati. Non serve l'intera cartella PROGETTO AMICO e non occorre installare strumenti di sviluppo per eseguire i test. Target attuale: Windows 10/11 x64, Pico RP2040 e GBA SP.

Su questo nuovo PC, se Celio non viene riconosciuto da PyUSB, conserva l'errore e usa CONTROLLA-USB.bat: la configurazione WinUSB del vecchio PC non viene trasferita dalla repository. I firmware UVC e Normal usano invece i driver USB standard di Windows. Non applicare un driver Celio al firmware Normal o UVC.

## Stato verificato

| Versione firmware | Risultato |
|---|---|
| Unificato / Smeraldo 0.6.0 (pacchetto 0.6.1) | Multiboot 7,70 s; 886 frame, 3,56 FPS medi, recupero dopo gap di 26,5 s. GBA super fluido secondo l'utente. |
| Smeraldo 0.5.1 | 261 frame validi; GBA fluido e transizioni recuperate secondo l utente; streaming 1,537 FPS, target 10 aperto. |
| Smeraldo 0.5.0 | 517 frame validi nelle due prove; 8,4-8,6 FPS prima dei blocchi. Rallentamento del gioco e nero dopo transizioni. |
| SD video 0.4.1 | 732 frame senza errori; scene FAST a 4,05 / 3,01 / 1,93 FPS. Target ancora aperto. |
| SD video 0.4.0 | 332 frame senza errori; RAW 1,33 FPS, fase RLE prolungata 3,55 FPS. Target 5-10 ancora aperto. |
| UVC 0.1.0 | Immagine sintetica 240x160 a 10 FPS visualizzata in Fotocamera; riapertura verificata dall'utente. |
| Link 0.2.0 / banco 0.3.4 | Multiplayer a cavo fisso: otto velocita pulite, conferma 60 s a 3451,4 B/s; screenshot completo in 23,45 s. |
| Normal 0.3.2 / 0.3.3 | Entrambe le prove senza header: 290664 parole, campioni registrati nulli su GP1 e GP3. Percorso del segnale da chiarire. |

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

Il motore grafico mGBA e incluso in runtime/mgba con licenza e provenienza. ROM commerciali, salvataggi, materiale completo del progetto amico e dipendenze di compilazione scaricate non fanno parte della repository. Vedi [attribuzioni](THIRD_PARTY.md). La repository e destinata all'uso privato; nessuna nuova licenza viene applicata ai componenti di terzi.

Piano successivo: [streaming e prodotto Smeraldo](PIANO-PRODOTTO-SMERALDO.md).
