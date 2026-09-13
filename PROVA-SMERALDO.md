# Avvio e collaudo unico 0.10.0

Versione pronta da eseguire, senza compilare. Nel confronto locale in mGBA, sullo stesso percorso con input direzionale, la cattura passa da 9,8 FPS (0.9.0) a 33,2 FPS. Il ciclo principale del gioco rimane vicino a 60 aggiornamenti/s. Sono misure emulatore: non certificano 30 FPS fisici o costanti in tutte le scene. Squadra e transizioni possono ancora scendere sotto il target.

## Avvio

1. Estrai tutto lo ZIP 0.10.0 in una nuova cartella scrivibile. Chiudi vecchi BAT e pagine del viewer.
2. **Mantieni il Pico 0.7.0: nessun nuovo flash.** Solo se provieni da firmware piu vecchi, installa dist/gbmirroring-unified-v0.7.0.uf2 con BOOTSEL. Conserva cavo e selettore nella posizione attuale.
3. Spegni il GBA, togli la cartuccia e riaccendilo. Apri **14-AVVIA-SMERALDO.bat** e premi **INVIO**: carica il nuovo loader 0.10.0. Non usare R per questo primo avvio, altrimenti rimane il vecchio residente.
4. Quando richiesto sul GBA, inserisci Smeraldo italiano originale e premi START. Entra nella partita.
5. Quando il programma PC indica PRONTO, premi **SELECT + L + R** sul GBA. Si apre http://127.0.0.1:8765. Attendi la prima immagine; il browser aggiunge un buffer di circa 200 ms.

## Una sessione di circa 10 minuti

Nella diagnostica registra la fase prima di provarla: fermo, cammino continuo, menu/squadra, entrata e uscita Centro Pokemon, battaglia, pausa/ripresa. Confronta sul GBA cattura attiva e in pausa (SELECT + L + R): il miglioramento del browser non deve costare fluidita o audio sulla console.

- **STREAM**: aggiornamenti verificati ricevuti dal GBA.
- **NEL BROWSER**: frame effettivamente mostrati, senza contare i refresh che ripetono l ultima immagine.
- **IMMAGINI CAMBIATE**: esclude gli stati visivamente identici; da fermo puo essere basso anche con uno stream regolare.

Le metriche sono finestre di cinque secondi: attendi che si stabilizzino. Non misurano gli FPS del gameplay GBA. Non sono implementati frame interpolati.

Al termine metti in pausa la cattura e premi **Termina e salva rapporto**. Invia l intera cartella **dist/emerald-reports/<data-ora>**, indicando se gameplay e audio sul GBA sono rimasti fluidi. Comprende rapporto.json, frames.jsonl, ultimo-frame.bmp, log e coda USB. Non serve fare prove separate di firmware o compilazione.

## Ripresa, OBS e recupero

R riprende il residente gia caricato nella stessa sessione della console. B, dopo spegnimento e nuovo avvio senza cartuccia, carica la baseline 0.8.0 mantenendo lo stesso Pico. Il pulsante Ripristina immagine richiede un riferimento completo senza cambiare cavo.

Per OBS usa una sorgente Browser **http://127.0.0.1:8765/?clean=1**, dimensioni 240 x 160 o multipli. Il BAT deve rimanere aperto. Il Pico non viene riconfigurato come webcam.

## Cosa cambia e limiti

La cache dei blocchi passa da 32 a 128 voci. Compressione RLE, LZ e patch dei registri/OAM vengono eseguite nella RAM veloce; eliminata una copia di 256 byte che veniva eseguita anche quando sarebbe stata scartata. Il trasmettitore mantiene lo stesso ordine dei bit e il limite di 155 parole per intervento. Nessun nuovo firmware Pico.

Pokédex e squadra usano le code di copia osservate e un controllo ciclico della VRAM, come l'overworld; un cambio di callback richiede una scansione completa. Gli altri callback mantengono la scansione conservativa. Le risorse nuove e i riferimenti completi richiedono ancora tempo: non e garantito il minimo di 30 FPS durante tutte le transizioni. Nel test squadra stabile la cattura resta circa 23 FPS; la finestra peggiore di un secondo nel cammino provato e circa 13 catture. Nessuna interpolazione o duplicazione di frame viene contata come un aggiornamento nuovo.

Gli effetti per scanline rimangono incompleti. La nuova versione va confrontata sul collegamento reale: invia una sola sessione con cammino continuo, menu/squadra, Centro Pokemon e battaglia.
