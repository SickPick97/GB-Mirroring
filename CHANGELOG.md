# Storico

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
