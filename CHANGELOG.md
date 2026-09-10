# Storico

## 0.3.7 - Scansione multiplayer locale

- Timing 125/60/30/10/1 per 20 s, arresto al primo errore e conferma 60 s della fase pulita con velocita misurata migliore.
- Esiti distinguono scansione completa e conferma dopo errore. Sequenza PIO e programma GBA invariati. Hardware PASS: cinque fasi pulite e conferma 60 s a timing 1, 4328,7 B/s.


## 0.3.6 - Misura multiplayer locale sul Pico

- Nuovo firmware Pico SDK/CDC, sequenza PIO master derivata da Celio; verifica locale CRC/pattern/sequenze, due finestre 30 s senza inviare dati grezzi USB.
- Nuovi BAT 8 e 9, caricatore del GBA invariato 0.2.0 via Celio e cambio manuale firmware mantenendo il GBA acceso. Nessuna inversione del cavo.
- Hardware PASS 2026-09-10: 1866,1 e 3719,4 B/s a timing 1000/125, zero errori e pio_fdebug zero. Nuova implementazione validata in due finestre da 30 s, non strumentazione del vecchio binario Celio.


## 0.3.5 - Profilo lato PC e contatori GBA

- Tre finestre da 30 s, contatori seriali GBA gia presenti ora esposti; letture USB e coda del parser misurate tramite wrapper senza modificare vendor o firmware.
- Hardware PASS: 3451,3 B/s, contatori GBA coerenti, coda campionata fino a 20 parole, letture USB circa ogni 10,17 ms. Screenshot completo in 22,26 s. Tempi USB includono attesa, non sono timestamp sul Pico.


## 0.3.4 - Multiplayer esteso a cavo fisso

- Nuovi avvii portatili per scansione da timing 1000 a 1, arresto al primo errore, conferma 60 s e screenshot conservativo.
- Firmware e vendor invariati. Ripristinare Celio prima della prova.
- PASS richiede anche conferma pulita e screenshot senza CRC errati. Test Normal invertito mantenuto come alternativa diagnostica.
- Hardware 2026-09-10: otto fasi pulite, 3451,4 B/s nella conferma di 60 s, screenshot completo in 23,45 s. Plateau da timing 125; nessuna inversione del cavo.


## Riscontro hardware 2026-09-10 (nessun nuovo firmware)

- Normal 0.3.3 confermato in esecuzione su GP3, ma ancora senza header: spostare il ricevitore non ha risolto.
- Archiviato riepilogo dei tre file coerenti, senza identificativi USB del PC. Prossima verifica: orientamento del cavo e percorso fisico del segnale.


## 0.3.3 - Ricezione SD per cavo GBA

- Ricevitore spostato da GP1/SI a GP3/SD, percorso usato dal trasporto multiplayer esistente. Tutti i pin restano ingressi.
- Log 0.3.2: 290664 parole, esattamente una fase completa; campioni registrati nulli e nessun header. Il CRC nullo non indicava integrita.
- Sender invariato. Nuovo percorso da verificare su hardware.


## 0.3.2 � Diagnostica della ricezione

- Ricevitore Pico: contatori grezzi, primi campioni, pin e stato PIO ogni due secondi anche senza BEGIN valido. Nessuna modifica al pilotaggio delle linee.
- Il PC registra e mostra la diagnostica; i messaggi periodici non impediscono il timeout.
- Corretto il cavo nella guida: l'utente conferma di avere sempre usato GBA. Sender GBA 0.3.0 invariato.
- Non dichiarata risolta la mancata ricezione: serve il nuovo rapporto hardware.

## 0.3.1 — Portabilita e repository

- Repository organizzata per aggiornamenti e risultati dei test.
- Runtime Windows e soli moduli Celio necessari inclusi nel pacchetto privato.
- BAT, import Python e collegamenti della documentazione indipendenti dal nome utente e dalla cartella originale.
- Firmware invariati rispetto alla consegna 0.3.0.

## 0.3.0 — Banco seriale normale

- Sender GBA, ricevitore Pico PIO/DMA, raccolta USB CDC.
- Prove da 1 MiB e screenshot a 256 kHz e 2 MHz.
- Verifiche software superate; hardware ancora da collaudare.

## 0.2.0 — Banco multiplayer

- Multiboot diagnostico, misura Celio e screenshot VRAM.
- Hardware collaudato: cinque velocita pulite, 2623,9 B/s massimi e immagine completa.

## 0.1.0 — Webcam USB sintetica

- Firmware Pico UVC 240x160 YUY2 a 10/5 FPS.
- Visualizzazione a 10 FPS e riapertura in Fotocamera confermate dall'utente.
