# Piano 10 FPS e Smeraldo italiano

Decisione del 2026-09-11: mantenere il trasporto SC/SD verificato; ridurre il lavoro sul GBA e passare dalla bitmap allo stato grafico. Nessun nuovo firmware viene creato con questo piano. Obiettivo: circa 10 immagini nuove al secondo, schermo completo, misurando anche velocita del gioco e ritardo della cattura. Cartuccia italiana originale, cavo fisso, RP2040 e nessuna modifica interna.

## Evidenza che guida le scelte

La prova 0.4.1 ha 732 frame consecutivi senza errori. Scena 0 FAST: 4,05 FPS; rendering 51,68 ms, copia 32,04 ms, CRC 66,38 ms, codec/gestione riferimento 91,96 ms, invio 4,33 ms. Totale circa 246 ms. Rendering appartiene al generatore del banco; accelerarlo non dimostra accelerazione della cattura su Smeraldo. Anche togliendolo completamente resterebbero circa 195 ms.

Scena 1 FAST: keyframe RLE medi 12676 byte (18 campioni), delta RLE medi 20797,5 (158 campioni). Scena 0: 6333,4 byte RLE contro 649 delta. Sono gruppi di frame diversi, non un confronto sullo stesso identico frame, ma il delta obbligatorio non e una scelta adeguata allo scorrimento. La successiva selezione codec va verificata sugli stessi input.

Tempi GBA dell invio nella scena 1: circa 19966,9 byte / 81,53 ms = 245 kB/s durante la routine, non throughput disponibile al gioco. 10 immagini RGB555 grezze richiedono 768 kB/s. A 245 kB/s un frame grezzo richiederebbe circa 313 ms. I 245 kB/s non possono essere utilizzati continuamente lasciando tutta la CPU al gioco: il sender GPIO occupa ARM7 mentre invia.

## Opzioni e priorita

1. Riduzione delle scansioni e copie (priorita immediata). Unire confronto, rilevamento blocchi cambiati e aggiornamento del riferimento; eliminare il buffer XOR materializzato e la copia integrale del riferimento. Elaborare parole allineate e buffer piccoli. Codice critico gia in IWRAM: non contabilizzare di nuovo quel guadagno.
2. Codec adattivo per blocchi (priorita immediata). Scegliere RAW, RLE oppure delta, con limite di lavoro e abbandono precoce se non conviene. Considerare byte risparmiati e cicli spesi. Non eseguire sempre tre compressioni complete. Ridurre keyframe completi periodici usando aggiornamenti assoluti di blocco e risincronizzazione progressiva.
3. Integrita proporzionata ai dati (priorita immediata). CRC di header, indirizzo/versione e payload effettivamente trasmesso. Conservare verifiche complete del decoder e verifiche dello stato ricostruito periodiche/in diagnostica, oppure checksum per blocco aggiornati soltanto quando cambia. Il CRC sul PC da solo non verifica il Link; deve esserci un valore di controllo prodotto sul GBA. Non sostituire tutto con un checksum piu debole.
4. Copie ARM a 32 bit / DMA (misurare). DMA utile per copie brevi e coerenti, non CPU gratis: sul GBA la CPU viene sospesa durante DMA. Disponibilita dei canali, tempi video e audio vanno rispettati; non applicare al gioco i canali/timer che il banco si appropria liberamente.
5. Cache di tile, mappe, palette e sprite sul ricevitore (massimo potenziale per Smeraldo). Esportare inizialmente le risorse necessarie e poi aggiornamenti e registri, senza ricomporre RGB555 sul GBA. Lo scorrimento puo modificare registri e strisce di tile anziche tutti i pixel. La quantita reale va misurata, specialmente battaglie e cambi scena.
6. Trasporto piu veloce (secondario). Conservare FAST/BASE. Provare ulteriori routine o forme d onda DMA solo dopo aver ridotto i dati e misurato cicli, RAM, jitter e carico del gioco. DMA non genera automaticamente i bit senza costo. PIO del Pico non esegue il lavoro della CPU GBA.
7. Normal SIO hardware (riserva diagnostica). Potrebbe alleggerire la CPU rispetto al GPIO, ma le prove a cablaggio fisso non hanno trovato il percorso dati. Nessuna promessa che il firmware possa rimappare SD su un pin hardware diverso. Inversione resta una prova opzionale separata, non requisito del percorso principale.
8. Riduzione qualita (ripiego esplicito). Minore profondita colore, palette indicizzata o risoluzione inferiore possono ridurre dati ma non risolvono residenza e acquisizione dei modi grafici. Preferire prima formati indicizzati nativi senza perdita; non sacrificare qualita automaticamente. Compressione pesante tipo JPEG/video non e la prima scelta per ARM7. Simulare la partita sul PC da input/coordinate non garantisce lo stesso schermo del GBA.

## Sequenza operativa con criteri di avanzamento

A. Una iterazione del banco per lavoro riutilizzabile: percorsi a blocchi, codec adattivo e CRC sui dati inviati. Confronto vecchio/nuovo su identici frame, non solo FPS delle barre. Profilare cicli, dimensione e RAM; distinguere render del generatore dal costo di cattura. Criterio: pixel ricostruiti corretti, recupero perdite, miglioramento misurato; non vincolare tutto il progetto al raggiungimento di 10 FPS nella scena casuale.

B. Prima del payload video completo, traccia grafica di Smeraldo in mGBA: VRAM, palette, OAM, registri e modifiche per scanline per una sequenza ripetibile (cammino, testo/menu, battaglia, transizione). Ricostruire soltanto dai dati esportati e confrontare pixel per pixel al renderer di riferimento. Misurare distribuzione byte/cattura e picchi, non solo media. Nessuna copia ROM deve essere necessaria sul ricevitore per inventare lo schermo; eventuali asset vengono esportati dal gioco. Non distribuire ROM o salvataggi.

C. Payload residente minimo BPEI: verificare le routine della revisione italiana, riserva RAM, stack, IRQ e callback prima di aggiungere il video. Le quattro firme esistenti sono solo un controllo preliminare. Prima prova: avvio e permanenza del payload con contatore/telemetria, mantenendo gioco, audio, menu e salvataggio corretti. Non trasportare nel gioco i circa 230 KiB dei tre buffer del banco. Mappare e riservare esplicitamente anche IWRAM; non assumere che lo spazio libero nel multiboot resti libero nel gioco.

D. Stream grafico incrementale: cattura in un punto coerente con gli aggiornamenti video, piccoli buffer e invio a blocchi interrompibile fra pacchetti. Dare tempo alla CPU del gioco; misurare occupazione CPU e confronto temporale con il gioco senza payload. Esempio di vincolo: a circa 245 kB/s, 10 kB occupano circa 41 ms soltanto di sender; 1 kB circa 4 ms. Budget utilizzabile va ricavato dal gioco, non dai 100 ms tra immagini. Il lavoro puo essere distribuito su piu refresh GBA, senza assumere VBlank interamente libero.

Protocollo: numeri di generazione, blocchi assoluti/versionati, controllo d integrita, commit dell immagine quando tutti i pezzi necessari sono coerenti. Una cache aggiornata in momenti diversi non costituisce automaticamente uno snapshot fedele. Se un asset viene sovrascritto mentre si trasmette, serve staging/versionamento o scarto della generazione: mai mescolare silenziosamente due frame. Ridurre accodamento verso l immagine piu recente solo preservando le dipendenze; prevedere reinvio senza affidarsi a un canale ACK bidirezionale non ancora implementato.

Obiettivo di accettazione: circa 10 FPS nuovi sostenuti nel normale gioco, menu e testo corretti, assenza di artefatti e velocita della partita confrontabile con il riferimento. Quantificare separatamente eventuali cali/transizioni e ritardo; non chiamare 10 FPS la ripetizione di immagini vecchie. Rumore casuale e cambi completi costituiscono limiti di banda; se l obiettivo non e rispettato, riportare quale limite rimane senza abbassare silenziosamente il criterio.

E. Webcam autonoma: verificare presto il bilancio RAM/cicli RP2040 (cache grafica, buffer video, USB, firmware). Renderer PC consente sviluppo e confronto ma non prova che il renderer completo entri nel Pico. Selezionare buffer a righe/tile e formato UVC compatibile per evitare copie complete multiple. Integrare UVC reale dopo stream grafico verificato, mantenendo questa fattibilita sotto controllo prima di investire tutto sul PC.

## Punti tecnici da verificare per Smeraldo

La decompilazione mostra sGpuRegBuffer e aggiornamenti video in VBlank. Sono candidati concreti per recuperare registri che non si possono leggere correttamente dall hardware. Non coprono automaticamente tutte le scritture dirette o gli effetti per scanline: gScanlineEffectRegBuffers e DMA0 sono un caso esplicito. Le strutture e gli indirizzi della ROM italiana vanno verificati; gli indirizzi della decompilazione inglese non sono trasferibili automaticamente. Un normale programma residente non intercetta magicamente tutte le scritture a VRAM/registri: scegliere callback e sorgenti realmente accessibili, confrontandoli alle tracce.

## Fonti e misure

- test-results/2026-09-11-sd-video-v0.4.1/summary.json e sorgenti firmware/sd-video.
- https://github.com/pret/pokeemerald/blob/master/src/gpu_regs.c
- https://github.com/pret/pokeemerald/blob/master/src/main.c
- https://github.com/pret/pokeemerald/blob/master/src/scanline_effect.c
- GBATEK, copia locale analisi/fonti/gbatek.html: DMA, temporizzazioni e memoria.

Non e ancora una dimostrazione di 10 FPS su Smeraldo. Il piano identifica le misure e le condizioni che rendono verificabile ogni passaggio, mantenendo fissi console, cavo e adattatore.
