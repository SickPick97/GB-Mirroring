# Decisione trasporto e verifiche 0.4.0

Il target utente e ora almeno 5-10 FPS con schermo completo, nessuna modifica hardware. Valutate:

- Multiplayer standard: stabile fino a 4328,7 B/s; 5/10 FPS grezzi richiedono 384000/768000 B/s, quindi la sola riduzione delle pause e insufficiente.
- Normal hardware: piu rapido ma il percorso SO non arriva al Pico nel verso di cavo attuale; prova con inversione conservata come alternativa diagnostica, non soluzione al requisito.
- UART/JOYBUS: non scelti come scorciatoia; segnali e ruoli vanno verificati e non creano un'uscita LCD. Nessun vantaggio dimostrato sul cablaggio corrente.
- GPIO sincrono SC/SD: entrambe le linee sono collegate. Il GBA puo pilotarle tramite RCNT; il Pico resta passivo. Scelto per il nuovo prototipo software.
- Compressione pixel: utile dove l'immagine e ridondante, con fallback RAW per non espandere il flusso. Stato grafico/tile con renderer resta possibile per i giochi, ma richiede acquisizione coerente e residenza.

Sorgente tecnica: https://github.com/afska/gba-link-connection/blob/master/docs/gbatek.md , sezione SIO General-Purpose Mode. RCNT 0x8030 abilita solo uscite SC e SD; SI/SO restano ingressi. L'uscita Pico non pilota nessuna linea Link. Il codice e originale del progetto, non una modifica del vendor Celio.

Build: python tools/build_sd_video.py. Tests: python tools/test_sd_video.py (dipendenza di sviluppo Unicorn gia locale), runtime/python/python.exe tools/check_portable.py. Il build usa codice/rodata in IWRAM e BSS in EWRAM; la piccola sezione boot multiboot copia il codice prima del salto. La routine ASM emette MSB-first, dato stabile con SC basso e campionamento su fronte alto; variante L aggiunge NOP. Il baud elettrico non si deduce dall'emulazione: va misurato sull'hardware.

Protocollo: header 12 parole little-endian [B47E,5647,0400,codec,seq_lo,seq_hi,payload_words,38400,pixel_crc32_lo,pixel_crc32_hi,header_crc16,5AA5]. Header CRC16 CCITT sui byte delle parole 2..9; pixel CRC32 IEEE sui 76800 byte RGB555. RLE16: token bit15=run, bit0..14=count nonzero, poi colore; token bit15=0: count letterali. Lunghezza massima payload38400 parole; decodifica sempre38400 pixel. Nessun delta dipendente da frame precedente. FIFO/DMA overflow arresta il ricevitore, non produce PASS.

Le scene animano direttamente VRAM e ne inviano una copia stabile; non servono asset PC. E homebrew cooperante, non cattura universale dalle cartucce. Obiettivo 10FPS del timer non equivale a prestazione raggiunta. Tempo CPU, convertitore di livelli, USB e scene possono ridurre gli FPS. Se serve CPU al gioco, occupazione del sender andra misurata e limitata.
