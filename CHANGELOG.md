# Storico

## 0.9.0 - Pacchetti raggruppati e presentazione temporizzata

- Raggruppa piu aggiornamenti grafici sotto un solo header/CRC; controlla limiti e conteggio byte, mantiene compatibilita con la baseline. Scan delle maschere a parole e audit 8/24 blocchi, invece di 24/48. Avvio possibile a ogni VBlank; limite 155 parole per intervento mantenuto, costo totale da verificare sulla console.
- Corretto il controllo quando VCOUNT torna a zero; la scansione cede nelle linee visibili. Maschera finale vuota termina a 393, senza oltrepassare il limite. Test ARM dedicato.
- Residente Thumb/ARM 3936 byte, loader 5600 byte. Restano 816 byte prima dello stack. Pico 0.7.0 invariato. INVIO carica 0.9.0, B conserva 0.8.0.
- Integra renderer nativo, WebSocket, buffer 200 ms e contatore dei frame mostrati nel browser. Fonti native e licenza incluse.
- Ultimo confronto mGBA: 433/410 catture per 600 frame, 600 VBlank in entrambe le finestre. Non sono 43/41 FPS fisici, non certificano movimento, gameplay o audio. Il target riguarda il browser; preservare la fluidita GBA e requisito separato.
- Test ARM/protocollo, batch malformati, CRC, PIO, multiboot simulato, avvio mGBA, viewer e runtime portatile. Nessun test fisico avviato dall agente.
- Restano limiti: transazione globale e snapshot distribuiti, scansione completa fuori overworld, effetti scanline incompleti. Cache iniziale da ROM e trasporto a dipendenze separate non integrati. Non si dichiara completato tutto il piano o garantito il minimo 30 FPS hardware.

## Sviluppo dopo 0.8.0 - percorso PC e dipendenze

- Renderer C diretto, sorgenti mGBA fissati e inclusi con licenza; zero differenze su 900 immagini della sequenza di gioco emulata. Mediana 1,365 ms, p95 2,452 ms sulla macchina di sviluppo.
- WebSocket binario, buffer temporizzato 200 ms e telemetria browser. Test dei modi video, sprite/finestre/blending, socket, presentazione e pipeline senza dispositivi fisici.
- Gestore separato di risorse immutabili con attesa delle dipendenze e controlli su contenuti, epoca, ordine e memoria. Non ancora integrato nel residente/Link.
- Prova isolata del residente Thumb/ARM: recuperati 880 byte, conteggi emulati equivalenti alla baseline. Build soltanto locale e test dedicati; firmware pubblicati invariati.
- Nessun nuovo firmware o tag: 30 FPS hardware, cache automatica e nuovo trasporto restano da completare. Stato in docs/SVILUPPO-30-FPS.md. Release 0.8.0 immutata.

## Analisi hardware 0.8.0 e piano 30-60 FPS

- 3119 frame consecutivi, 10,2575 FPS medi, zero CRC/header/recuperi/salti. Intervalli mediana 60,1 ms, p95 228,2 ms; utente segnala scatti soltanto sul PC. Evidenza selezionata in test-results/2026-09-12-emerald-v0.8.0.
- Utente accetta ritardo 150-250 ms e cache locale automatica dalla cartuccia. Piano strutturale in PIANO-STREAMING-30-60.md: stato rapido, risorse versionate, renderer diretto e presentazione temporizzata. Target minimo circa 30, obiettivo 50+; fattibilita per tutte le scene ancora da verificare.
- Nessun sorgente applicativo, firmware, binario o numero di versione modificato.

## 0.8.0 - Cadenza piu rapida e visualizzatore web

- Hardware 0.7.1: 1059 frame consecutivi, 5,805 FPS medi tra arrivi verificati, gap massimo 2,836 s, tre keyframe. Una richiesta di recupero; 31 payload e 18 header recuperati. Utente conferma scomparsa dei blocchi alternati e migliori transizioni. Evidenza selezionata in test-results/2026-09-12-emerald-v0.7.1.
- Obiettivo aggiornato: la pagina web e l uscita definitiva; UVC autonoma non piu richiesta.
- Avvio cattura ogni 3 VBlank invece di 6; audit 24 blocchi quando rapido, 48 se trascorrono almeno 6 VBlank. Limite di trasmissione per intervento resta 155 parole, soglie VCOUNT e slot feedback invariati. Il maggior numero di catture e la compressione aumentano comunque il lavoro totale, da verificare sul GBA.
- Codec locale LZ di parole, senza cache aggiuntiva persistente: usa riferimenti a sequenze gia presenti nello stesso blocco, solo se piu corto del precedente formato. Costi limitati a 128 parole, decoder con limiti su riferimenti e lunghezze. Sul campione di 200 blocchi raw/RLE della coda hardware: payload 48888 -> 37202 byte (-23,9%); non e una misura dell intero stream.
- Pagina rinnovata, schermo intero, vista OBS pulita, diagnostica richiudibile e metriche distinte. Richieste video senza ritrasmissione dei frame invariati; statistiche aggiornate separatamente una volta al secondo.
- Nuovo loader 0.8.0 pronto; Pico 0.7.0 invariato. B avvia la baseline 0.7.1. Controlli ARM, codec, CRC, viewer HTTP, multiboot simulato e mGBA; in emulazione circa 18 catture/s, non una promessa di FPS hardware. Nessuna modifica al cavo o alla console.

## 0.7.1 - Riduzione dei ripristini e recupero degli errori singoli

- Test hardware 0.7.0: 1038 transazioni, 4,605 FPS tra arrivi verificati, gap massimo 8,609 s, 16 keyframe e 21 richieste di recupero. Utente segnala pause ripetute; evidenza selezionata in test-results/2026-09-12-emerald-v0.7.0.
- Decoder: ricerca limitata di un bit invertito, inserito o perso; accetta soltanto una soluzione unica verificata dal CRC. Header riparati verificati anche contro CRC payload. Errori multipli restano scartati. Le code reali consentono il recupero di tre header e un payload; replay parziale, non certifica tutta la sessione.
- Ripristino automatico solo per errori irrisolti: nessuna richiesta per attesa iniziale, nessuna nuova richiesta causata da contatori storici dopo un frame valido, nessuna ripetizione durante una transazione in corso.
- Residente conserva il riferimento dopo reset Link a transazione completata e forza nuova verifica delle risorse. Trasmissioni interrotte con modifiche richiedono ancora un keyframe.
- Loader 0.7.1 pronto; Pico 0.7.0 immutato, nessun nuovo flash per chi lo usa gia. Test ARM, errori sintetici, multiboot simulato, viewer e mGBA; prestazioni hardware della correzione ancora da misurare. Keyframe completi e costi di cambi scena non eliminati; 10 FPS hardware non garantiti.

## 0.7.0 - Scansione selettiva e recupero su richiesta

- Osservazione read-only delle code DMA3 e sprite BPEI prima dell IRQ originale. Nell overworld: dirty mask e audit progressivo; negli altri callback resta la scansione completa.
- CRC compatti, buffer di compressione riutilizzato e dizionario 32 voci. Risoluzione e colori invariati; limite di 155 parole per intervento conservato.
- Finestra half-duplex dopo END per conferma/richiesta di keyframe; Pico si arma solo dopo END identificato con CRC e rilascia SD a fine finestra. Se il feedback manca rimane il refresh periodico. Percorso elettrico da collaudare.
- Ricezione, decodifica e rendering separati; coda presentazioni limitata. Recupero automatico/manuale, tracce attorno agli errori, fasi della prova e modalita Browser pulita. Opzione B avvia il loader 0.6.0 con lo stesso firmware Pico.
- Test: 6 residente/protocollo, 2 modello PIO, 2 multiboot CDC, 10 viewer/SD; firme e build verificate. In mGBA 92/93 catture per 600 frame (9,16/9,26 FPS), 600 VBlank gioco in entrambe le finestre. Non certifica prestazioni hardware o gameplay/audio.
- Questa consegna non completa tutto il piano: restano commit per risorsa, aggiornamenti piu fini, effetti scanline e renderer UVC autonomo. Nessuna dichiarazione di 10 FPS hardware prima del test.


## Piano prodotto dopo conferma fluidita 0.6.1

- Utente conferma GBA super fluido. Piano unico per stato grafico rapido, risorse versionate, riduzione CPU/byte, recupero, uscita webcam e collaudo integrato.
- Analisi aggiuntiva: transazioni senza cambiamenti mediane 7 interventi, con cambiamenti non-keyframe 21; il costo della scansione completa resta strutturale.
- Nessun codice o binario modificato. Piano in PIANO-PRODOTTO-SMERALDO.md.


## Riscontro hardware pacchetto 0.6.1

- Multiboot unificato in 7,70 s, zero desync/riavvii; streaming nella stessa sessione.
- 886 transazioni valide, 3,559 FPS medi; 446 senza blocchi cambiati. Gap di 53 sequenze per 26,487 s, recupero su keyframe; 52 delta non applicabili e un errore di validazione da diagnosticare.
- Conteggi e lunghezze verificati; 304 pacchetti della coda finale con CRC validi. Evidenza ripulita in test-results/2026-09-11-emerald-v0.6.1. Nessun binario modificato.


## 0.6.1 - Correzione avvio Python portatile

- Aggiunta esplicita della cartella tools al percorso import del launcher: il runtime isolato non aggiunge automaticamente la directory dello script.
- Test diretto dello script con il Python incluso, da cartella con spazi e directory corrente diversa, uscita prima di USB. Il precedente test di import aggiungeva il percorso manualmente e mascherava il difetto.
- Firmware Pico e loader GBA 0.6.0 invariati: nessun nuovo flash necessario.


## 0.6.0 - Avvio unico, cache e misure integrate

- Firmware RP2040 unico CDC CAFE:4024: multiboot master PIO, rilascio bus e ricezione SD PIO/DMA senza cambio UF2. Trasporto PC per il multiboot esistente, moduli vendor invariati.
- Avvio 14 con controllo file, multiboot, viewer e rapporti nella stessa sessione; modalita R per ripresa senza boot.
- Cache di 64 risorse, RAW/RLE/riferimenti e patch di registri/OAM; scanner ARM in IWRAM. Tetto 155 parole per intervento e telemetria, lettura USB separata dal rendering.
- Test software: 5 residente/protocollo, 10 viewer/SD, 2 multiboot CDC/PIO; verifiche UF2 e portabilita. mGBA circa 6,47 FPS statico, 3,68 con input direzionale e 600/600 VBlank. Non prova prestazioni hardware o intera partita.
- Target 10 FPS non raggiunto: code di copie del gioco, commit basato sulle risorse e UVC restano aperti.


## Riscontro hardware 0.5.1 e piano streaming/firmware unico

- Utente conferma GBA fluido e assenza di nero persistente nelle transizioni provate. 261 frame validi, 1,537 FPS fra primo e ultimo, nessun errore CRC o sequenza.
- Analizzati limiti scheduler, distribuzione byte e coda USB. Piano per aggiornamenti grafici fini, riuso risorse e firmware unico multiboot/video.
- Solo documentazione ed evidenze selezionate; nessun sorgente, binario o versione firmware modificato.


## 0.5.1 - Priorita al gioco e recupero del flusso

- Test: 4 residente/protocollo, 9 SD/HTTP; mGBA 600/600 VBlank statico e con input direzionale, circa 2,49 catture/s statico dopo warmup. Non misura diretta della fluidita hardware.

- Registrate due prove hardware 0.5.0: cattura dalla cartuccia riuscita, 517 frame, rallentamento percepito e nero persistente dopo transizioni.
- Residente a lavoro limitato: massimo 64 blocchi confrontati e un blocco trasmesso per IRQ; rinvio fuori VBlank o a callback molto tardivo. Non implica permanenza completa entro VBlank.
- Snapshot raccolto su piu fotogrammi: meno blocchi lunghi del gioco, ma streaming piu lento e possibili incoerenze transitorie durante movimento/cambi scena.
- Decoder riallinea i pacchetti a qualsiasi bit, con validazione CRC e compatibilita 0.5.0. La perdita di allineamento e un ipotesi supportata dai sintomi, non dimostrata dai vecchi log.
- Conservata coda USB di 64 KiB locale per diagnosi; Pico 0.4.0 e cavo invariati. Nuovo loader 0.5.1, nessun binario pubblicato sovrascritto.


## 0.5.0 - Primo residente sperimentale Smeraldo italiano

- Loader BPEI con controllo CRC del bootstrap, residente IRQ e sender IWRAM. Nessuna modifica alla ROM; cavo e Pico SD 0.4.0 invariati.
- Esportazione dei soli blocchi grafici cambiati, CRC dei pacchetti, transazioni complete e recupero tramite keyframe. Renderer mGBA portatile incluso: non richiede ROM commerciali sul PC.
- Avvii 12/13, istruzioni PROVA-SMERALDO.md, rapporti e anteprima locale. Nessuna UVC reale o riproduzione completa degli effetti per scanline.
- Banco homebrew 0.4.2: confronto a blocchi e CRC sul payload codificato, riduzione copie e lavoro rispetto a 0.4.1.
- Verifiche software: 9 test SD, 3 test residente/protocollo; avvio mGBA e 90/90 immagini esatte nella sequenza provata. Campo statico emulato: 9,46 catture/s e 56,74 VBlank gioco/s. Hardware e intera partita non certificati.


## Piano prestazioni e Smeraldo

- Analizzati costi CPU, delta penalizzante nello scorrimento e budget del sender. Definito PIANO-10FPS-SMERALDO.md con priorita, criteri di verifica e integrazione grafica BPEI. Nessun software o firmware modificato.


## Riscontro hardware 0.4.1

- 732 frame senza errori; scene FAST 0/1/2 a 4,05/3,01/1,93 FPS. Preparazione CPU dominante sulla scena 0 (circa 242 ms contro 4,33 ms TX). Firmware invariato, target FPS aperto.


## 0.4.1 - Sender ottimizzato e delta video

- Routine ARM srotolata FAST, BASE conserva il sender 0.4.0; Pico invariato.
- Ridotte divisioni nella scena, compressione XOR/RLE con keyframe ogni 10 frame e recupero dopo perdita.
- Header protetto esteso: scena, modalita e tempi GBA di rendering/copia/CRC/codec e trasmissione precedente.
- Verifica ARM dei pixel e delle due routine, compatibilita 0.4.0 e recupero delta. Prestazioni hardware e Smeraldo ancora da implementare/verificare.


## Riscontro hardware 0.4.0

- Verificati 332 frame consecutivi senza errori; RAW 102229 B/s e 1,33 FPS, fase RLE prolungata 3,55 FPS. Obiettivo 5-10 FPS ancora aperto; firmware invariato.

## 0.4.0 - Video su protocollo software SC/SD

- Nuovo sender GBA GPIO in IWRAM e ricevitore Pico passivo PIO/DMA, stesso cavo e orientamento; supera il vincolo strutturale di una parola utile per ciclo multiplayer. Banda effettiva ancora da verificare.
- Video completo 240x160 letto da VRAM, RLE16 lossless con fallback RAW, CRC32 pixel e CRC16 header. Tre scene, controlli RAW e impulsi piu lenti.
- Visualizzatore browser locale via driver CDC Windows, FPS di frame nuovi verificati e registri automatici. Nessuna cartuccia o webcam UVC in questo banco.
- Test ARM del sender GPIO e dei pixel, decoder con errori e pipeline HTTP simulata; nessuna dichiarazione di 5-10 FPS reali prima del collaudo.


## Studio video offline (firmware invariato)

- Valutata distinzione segnale LCD / dati grafici esportati. Ricostruzione PC ammessa nel prototipo, UVC autonomo resta requisito finale.
- Aggiunto studio riproducibile compressione/delta con verifica lossless su schermate homebrew e caso sintetico poco comprimibile. Nessuna previsione FPS sui giochi.


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
