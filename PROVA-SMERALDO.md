# Smeraldo - pacchetto integrato 0.6.0

Un firmware Pico per multiboot e video; un solo avvio PC, controlli offline e misure automatiche. Cavo e GBA invariati. Non servono ROM sul PC o strumenti di compilazione. Questa e una versione sperimentale: primo collaudo del firmware unificato, non webcam UVC autonoma.

## Preparazione unica

1. Estrai tutto il pacchetto in una cartella nuova e scrivibile. Chiudi gli altri programmi dell adattatore.
2. Spegni il GBA e rimuovi la cartuccia. Collega il Pico via USB tenendo BOOTSEL e copia dist/gbmirroring-unified-v0.6.0.uf2 su RPI-RP2. Attendi il riavvio USB.
3. Mantieni il cavo come sempre: piccolo nell adattatore, grande nel GBA, selettore GBA, presa centrale vuota. Accendi il GBA senza cartuccia.

## Una sola procedura

4. Avvia 14-AVVIA-SMERALDO.bat. Verifica automaticamente i file. Premi INVIO per il nuovo multiboot. Non scegliere R durante questo primo avvio.
5. Quando il GBA mostra INSERT CART THEN START, lascialo acceso, inserisci Smeraldo italiano originale e premi START. Se appare WRONG CART OR REVISION, fermati e segnala il messaggio.
6. NON cambiare firmware, non scollegare USB e non chiudere il BAT. Il programma passa da solo alla ricezione video e apre la pagina locale.
7. Entra nella partita; quando la console PC dice PRONTO premi insieme SELECT+L+R e rilasciali. Attendi fino a 15 secondi per la prima immagine.
8. Nella stessa sessione: resta fermo 30 secondi, cammina per 60 secondi, entra/esci dal Centro Pokemon, apri/chiudi la squadra e il menu. Metti in pausa la cattura con SELECT+L+R per 10 secondi e confronta la velocita del GBA; riattivala e continua per altri 30 secondi. Tutte le misure vengono raccolte automaticamente, senza altri BAT o prove di banda separate.
9. Metti in pausa con SELECT+L+R, poi premi Termina e salva rapporto nella pagina. Spegni il GBA prima di rimuovere la cartuccia. In questa prova evita progressi che vorresti salvare: compatibilita dell intera partita e salvataggio con residente non certificati.

Invia la cartella dist/emerald-reports/<data-ora> intera: rapporto.json, frames.jsonl, ultimo-frame.bmp, usb-tail.bin, console.txt e multiboot.json se presenti. In caso di errore prima del viewer e disponibile anche avvio-<data-ora>.txt nella cartella emerald-reports.

## Ripresa e problemi

- Se chiudi il programma lasciando il gioco acceso: metti prima in pausa la cattura, riapri lo stesso BAT e scegli R. Attendi PRONTO, quindi riattiva SELECT+L+R. R non ricarica il payload.
- Dopo spegnimento o soft reset del GBA occorre il multiboot da slot vuoto: scegli INVIO. Il firmware Pico resta installato; BOOTSEL serve solo per installazione e aggiornamenti futuri.
- Nessun Pico trovato: verifica di aver installato UNIFIED 0.6.0. Usa il driver CDC standard Windows, senza Zadig.
- Multiboot fallito: conserva la cartella/console. Spegni il GBA prima di riprovare; non aggiungere cambi UF2 alla procedura.
- Immagine assente dopo 15 secondi: termina e conserva i log. Nessuna inversione del cavo. Un reinvio completo puo essere richiesto mettendo in pausa e riattivando la cattura.

## Cosa cambia e cosa e verificato

Cache di 64 risorse grafiche sul ricevitore, riferimenti per contenuti ripetuti, RLE selettivo e modifiche parziali di registri/OAM. Scansione dei blocchi invariati in IWRAM. Limite di 155 parole inviate per intervento, confronto con deadline video e telemetria integrata. Ricezione USB PC su thread separato con coda limitata. Conservati CRC e recupero dell allineamento a bit.

Verifiche software: avvio BPEI, rifiuto firma errata, decodifica delle scritture ARM reali, errori protocollo, multiboot attraverso trasporto CDC simulato, viewer HTTP e pacchetto portatile. Campo statico emulato: circa 6,47 catture/s; input direzionale circa 3,68 catture/s, 600 VBlank gioco su 600 in entrambe le finestre. Questi non sono risultati hardware. I 90 confronti esatti del renderer riguardano snapshot coerenti del test, non tutta la cattura distribuita del gioco.

L obiettivo 10 FPS non e ancora raggiunto nei test. Restano da implementare rilevamento selettivo delle modifiche del gioco e gestione delle risorse dipendente dallo stato; non sono inclusi effetti per scanline o UVC. La cattura resta distribuita nel tempo: possibili artefatti temporanei e ritardo ai cambi scena. Il contatore VBlank non prova da solo fluidita del gameplay o dell audio.
