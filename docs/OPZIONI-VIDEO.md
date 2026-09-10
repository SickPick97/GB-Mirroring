# Valutazione uscita video via Link

## Decisione

Il Link non espone il segnale LCD ne offre un accesso remoto arbitrario alla memoria. Il firmware Pico da solo non puo estrarre il video interno. Il controller video compone sfondi e sprite; la CPU gestisce memoria e registri. Nessuna modifica interna al GBA: restano necessari codice residente/cooperante, esportazione via SIO e ricostruzione.

La ricostruzione sul PC e utile nel prototipo: sposta il rendering fuori dal GBA, ma non elimina acquisizione, residenza, banda o coerenza. Per il risultato finale UVC autonomo rendering/decodifica dovranno risiedere sull'adattatore. Non e ancora dimostrato che un renderer GBA completo rientri in RAM e tempi del RP2040; un prototipo PC funzionante non garantisce quel passaggio.

## Cosa esportare

- Bitmap: il nostro Mode 3 contiene 240x160 pixel RGB555, 76800 byte. E una base controllata, non la cattura universale di ogni modalita video.
- Stato grafico: VRAM (96 KiB), palette (1 KiB), OAM (1 KiB), registri e stato necessario. Nei modi a tile VRAM non contiene l'immagine finale gia composta. Registri non leggibili, effetti per scanline, DMA e modifiche durante il frame richiedono acquisizione/intercettazione coerente; una semplice fotografia della memoria non basta per fedelta universale.
- Trasmettere coordinate e ricreare una mappa non sostituisce la riproduzione dello schermo: menu, testi, battaglie ed effetti devono restare corretti.

## Lavoro svolto e seguito

Aggiunto tools/evaluate_graphics.py: lettura delle schermate gia verificate, compressione offline zlib e delta di blocchi 8x8, con decodifica/ricostruzione confrontata con l'originale. Report in test-results/offline-graphics-study/report.json. Tre schermate del medesimo homebrew: 918-922 byte compressi contro 76800 grezzi. Caso sintetico poco comprimibile: 75620 byte. Le schermate provengono da sessioni diverse, non costituiscono una sequenza video di gioco. Zlib qui gira sul PC; non e un codec implementato sul GBA e non dimostra FPS.

Proseguire sul trasporto multiplayer verificato a cavo fisso. Primo passo di implementazione video: keyframe bitmap completo e aggiornamenti di blocchi cambiati con numero frame, riferimento alla base, CRC e recupero tramite keyframe; verificare su animazione homebrew, incluse variazioni estese e perdita dati. Valutare encoder leggero sul GBA e carico CPU prima di scegliere zlib o altro formato. Poi introdurre esportazione dello stato grafico e renderer PC dove piu conveniente, con profili di gioco e acquisizione coerente. Non promettere un framebuffer universale o compatibilita automatica con tutte le cartucce.

Nessun nuovo test hardware richiesto per questa valutazione; firmware 0.3.7 invariato. L'inversione del cavo per Normal resta una diagnosi alternativa.

## Riferimenti

- https://gbadev.net/gbadoc/graphics.html - controller video, modalita bitmap/tile.
- https://gbadev.net/gbadoc/memory.html - VRAM, palette e OAM.
- https://www.akkit.org/info/gba_comms.html - segnali e protocolli SIO, pinout Link.
- GBATEK, copia locale analisi/fonti/gbatek.html - registri LCD, effetti HBlank e mappa memoria.
