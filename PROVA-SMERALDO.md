# Avvio e collaudo unico 0.9.0

Obiettivo: almeno 30 FPS nello stream del browser, conservando la fluidita normale sul GBA. Le misure emulatore superano 40 catture/s nelle finestre provate, ma i 30 FPS sul collegamento reale restano da confermare. Questa versione e pronta da eseguire; non serve compilare.

## Avvio

1. Estrai tutto lo ZIP 0.9.0 in una nuova cartella scrivibile. Chiudi vecchi BAT e pagine del viewer.
2. **Mantieni il Pico 0.7.0: nessun nuovo flash.** Solo se provieni da firmware piu vecchi, installa dist/gbmirroring-unified-v0.7.0.uf2 con BOOTSEL. Conserva cavo e selettore nella posizione attuale.
3. Spegni il GBA, togli la cartuccia e riaccendilo. Apri **14-AVVIA-SMERALDO.bat** e premi **INVIO**: carica il nuovo loader 0.9.0. Non usare R per questo primo avvio, altrimenti rimane il vecchio residente.
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

## Limiti dichiarati

Il batch riduce gli header e il lavoro di scansione; il renderer diretto riduce il costo PC. La transazione grafica resta globale e puo durare piu frame: non e ancora il trasporto a dipendenze separate del piano completo. Non e presente la cache iniziale da ROM. Fuori dall overworld resta una scansione conservativa, e gli effetti per scanline non sono completamente riprodotti. Transizioni e scene complesse possono scendere sotto il target. I conteggi emulatore e i VBlank non certificano da soli fluidita reale o 30 FPS sostenuti.
