# Piano dopo il collaudo Smeraldo 0.5.1

11 settembre 2026. Solo analisi e documentazione: nessuna modifica al software o ai firmware. Priorita: conservare la fluidita del GBA confermata dall utente e raggiungere almeno 10 aggiornamenti grafici reali/s nel normale gioco. Un ritardo moderato e accettabile. Secondo obiettivo: un unico firmware Pico per multiboot e ricezione video, senza cambi UF2 durante la sessione.

## Evidenza e limite attuale

Prova 20260911-101031: 261 frame, sequenze 0..260, zero CRC/header/riferimenti mancanti/gap/duplicati; cinque riagganci riportati, 104 byte scartati. Non equivalgono a cinque frame danneggiati. Arresto pulito. L utente conferma GBA fluido e assenza di nero persistente entrando/uscendo da Centro Pokemon e menu. Ultima immagine ispezionata: scena di gioco visibile; non certificazione pixel per pixel.

Tra primo e ultimo frame: 1,537 FPS su 169,135 s; intervallo mediano 0,586 s, massimo 7,049 s. Le immagini non complete iniziali/finali non entrano nella misura. Non-keyframe: media 20,83 blocchi cambiati, 5895 byte; mediana 21 blocchi. Quattro keyframe (0,49,75,159), ciascuno da 110102 byte.

Il codice impone massimo un blocco da 256 byte per IRQ e 64 confronti. A circa 59,73 refresh/s il tetto teorico dei soli blocchi e circa 15,3 kB/s, anche senza scansioni o altro lavoro. Una scansione dei 393 blocchi richiede almeno sette interventi anche a contenuto invariato. Questi sono limiti software, non la banda massima del cavo. Se un immagine a 10 FPS mantenesse la dimensione media attuale servirebbero circa 59 kB/s: e una proiezione, non una misura di cosa cambierebbe campionando ogni 100 ms.

Nella sola coda raw finale: 252 pacchetti riconosciuti, 230 blocchi con CRC verificato. RLE16 con fallback RAW ridurrebbe 58880 byte a 55976, circa 4,9%, esclusi header e costo CPU. Per 207 blocchi ricomparsi nella coda, una bitmap delle halfword modificate ridurrebbe idealmente 52992 byte a 30584, circa 42,3%. Quest ultimo e un confronto offline con riferimenti conservati sul PC: non dimostra che la stessa cache entri nel GBA o che il codec sia conveniente. La coda e parziale, non rappresenta tutte le scene.

## Architettura proposta per i 10 FPS

1. Misurare il budget prima di aumentarlo. Rilevare costo di confronto, copia, CRC e invio, tempo massimo per intervento, chiamate principali del gioco e code PC. Usare VCOUNT e strumenti emulati senza appropriarsi alla cieca di timer/DMA usati dal gioco. Confrontare cammino, testo, menu, audio e transizioni con cattura in pausa. Il contatore VBlank da solo non misura la fluidita del gameplay.

2. Separare aggiornamenti frequenti e risorse. Registri del display, scorrimento, OAM e palette devono poter produrre uno stato coerente ogni sei refresh circa. Tile e mappe gia disponibili sul ricevitore si riusano. Il rendering PC attende le versioni delle risorse effettivamente richieste da quello stato, non la scansione di tutti i 96 KiB di VRAM. Le nuove immagini devono provenire da nuovi stati del GBA; ripetere il canvas a 10 Hz non soddisfa il requisito.

3. Ridurre i dati alla fonte. Spedire intervalli/elementi realmente cambiati, blocchi piccoli per regioni dinamiche, riferimenti a risorse gia trasferite per animazioni ricorrenti e copie note. Conservare i dati grafici reali sul ricevitore: nessuna ROM Pokemon necessaria sul PC e nessuna simulazione del movimento del personaggio. Un indirizzo ROM immutabile puo identificare una sorgente; un indirizzo RAM da solo non basta per identificare contenuto che cambia. Cache e riferimenti devono avere generazioni e controllo d integrita.

4. Individuare gli aggiornamenti senza scansione completa obbligatoria. La decompilazione espone code di copie sprite, registri buffered e gestione DMA3. Verificare firme e indirizzi italiani; osservare code/callback accessibili prima che vengano svuotati, mantenendo scansioni di controllo per scritture non coperte. Non e possibile intercettare magicamente tutte le scritture o modificare codice nella cartuccia originale. Se un percorso non ha un punto di aggancio in RAM sicuro, usare scansione selettiva invece di assumere che sia intercettabile.

5. Scheduler con limite di tempo, non di numero di pacchetti. Conservare il budget misurato della 0.5.1 come riferimento iniziale. Molti comandi piccoli possono costare meno di un blocco RAW. Integrare confronto e checksum dove conviene, mantenendo CRC generato sul GBA. RAW per dati poco comprimibili; compressione economica solo se il risparmio di invio supera il costo CPU. Nessuna compressione pesante obbligatoria.

6. Coerenza e ritardo limitato. Piccolo staging GBA per i dati che rischiano di essere sovrascritti, versioni per risorsa, commit di stato sul PC. Il ritardo accettato permette di finire una generazione senza bloccare il gioco, ma non risolve una produzione media superiore alla banda disponibile. Accorpare/scartare solo stati superati preservando risorse e dipendenze. Obiettivo iniziale di buffering 0,5-1 s da misurare, non coda illimitata. Sulle transizioni ricostruire le risorse necessarie mantenendo l ultimo stato completo e segnalando aggiornamento in corso.

7. RAM esplicita. Il residente oggi dispone di una piccola regione EWRAM e di 0x600 byte nella coda IRQ IWRAM. Non aggiungere una copia completa da circa 100 KiB sul GBA. Valutare piccoli dizionari/riferimenti, staging e buffer riutilizzati dentro i limiti del linker; cache ampia e rendering restano su PC/Pico secondo risorse disponibili. La futura UVC autonoma richiede un bilancio RAM separato.

Criterio quantitativo: con lo stesso ordine di budget di invio della 0.5.1, puntare a circa 1-1,3 kB medi per stato a 10 FPS, con margine per controlli e picchi. E una soglia progettuale, non un risultato ottenuto. Prima di implementare tutto, raccogliere una traccia a intervalli di 100 ms e confrontare stesso input per formato attuale, intervalli e cache di risorse. Se la soglia non viene raggiunta, non promettere 10 FPS con il medesimo budget.

## Alternative valutate

| Opzione | Decisione |
|---|---|
| Cache risorse, aggiornamenti fini, scansione selettiva | Strada principale; riduce lavoro e byte sul GBA. |
| Solo RLE su blocchi attuali | Insufficiente nel campione ricevuto; usarla selettivamente. |
| Piu blocchi per IRQ senza misurare tempo | Non adottare: rischia di reintrodurre rallentamento. |
| Ottimizzare reader USB e renderer PC | Necessario per evitare arretrato a 10 FPS, ma non elimina le attese GBA attuali. Separare ricezione da rendering. |
| PIO/DMA Pico | Utili per ricevere e gestire USB; non liberano il GBA dalla generazione GPIO dei bit. |
| DMA GBA per forme d onda | Ricerca secondaria: sospende la CPU e richiede canali/buffer, non trasferimento gratuito. |
| SIO hardware Normal | Riserva sperimentale; cablaggio fisso non validato nelle vecchie prove. Non condizionare il percorso principale a inversione cavo. |
| Compressione video pesante, meno risoluzione/colori | Non prioritarie: prima sfruttare dati grafici nativi e riuso senza perdita. |

## Un firmware Pico per multiboot e video

Fattibilita alta: entrambe le funzioni sono gia state eseguite sullo stesso adattatore, in tempi diversi. Manca l integrazione e il collaudo del passaggio. Il repository contiene un master multiplayer PIO e un ricevitore SC/SD PIO/DMA. Proposta: un progetto Pico SDK/TinyUSB con un identita USB CDC stabile e un comando per cambiare modalita, senza riavviare o riscrivere flash.

Stati: inattivo con pin rilasciati; multiboot master; rilascio bus; ricevitore video passivo; pausa/errore. Durante il passaggio fermare master, DMA/IRQ associati e svuotare FIFO; impostare direzioni/pull prima di armare il ricevitore; inviare READY al PC. Nessun master e ricevitore che pilotino contemporaneamente il collegamento. La gestione dei buffer deve distinguere risposte multiboot, comandi e dati video.

Prima integrazione: mantenere il protocollo multiboot collaudato sul PC mediante un trasporto CDC compatibile con send_words/read_word/set_timing/drain_rx del modulo esistente. Accodare fasi deterministiche e non introdurre parole idle spurie; timing dei passaggi sensibili sul Pico. Non serve portare subito tutta la macchina multiboot sul microcontrollore o fondere alla cieca i binari Celio. La seconda opzione, spostare il multiboot completo sul Pico, rimane evoluzione possibile dopo il collaudo.

Un unico avvio PC orchestra caricamento, rilascio del bus e anteprima. Il caricatore multiboot mostra comunque quando inserire la cartuccia e premere START. Un solo UF2 da caricare all installazione o agli aggiornamenti futuri; nessun BOOTSEL o distacco USB durante una normale sessione. Dopo spegnimento GBA serve ancora il multiboot, ma non un nuovo flash Pico.

Questo unifica avvio e streaming del progetto. La webcam USB autonoma finale resta un lavoro ulteriore: il renderer PC attuale non diventa automaticamente un renderer RP2040 solo aggiungendo descrittori UVC.

## Ordine di sviluppo e prove

1. Archiviare questa prova come baseline e misurare tracce/costi a 100 ms, senza cambiare fluidita o trasporto.
2. Integrare firmware unico mantenendo il video 0.5.1: almeno dieci avvii consecutivi, cambio modalita senza USB scollegata, recupero dopo chiusura viewer/assenza GBA, nessuna regressione del gioco.
3. Implementare aggiornamenti fini e riuso risorse, decoder e staging versionato; verifiche ARM, memoria, CRC, perdite e cambi scena. Separare il lettore USB dal renderer PC.
4. Regolare budget e cadenza sui risultati, con buffer limitato. Verifica hardware nel campo, cammino continuo, dialoghi, squadra, Centro Pokemon e almeno una battaglia; confrontare con cattura spenta. Misurare FPS da stati nuovi, code, ritardo e peggiori tempi GBA, non soltanto medie.

Accettazione: almeno 10 nuovi stati/s sostenuti nelle scene ordinarie previste, con qualita e fluidita GBA comparabili alla 0.5.1; transizioni e picchi esplicitamente misurati e recupero automatico. Non dichiarare 10 FPS garantiti in qualunque scena prima di questi test. Il firmware unico e tecnicamente piu certo del target prestazionale.

## Fonti

- Dati locali: test-results/2026-09-11-emerald-v0.5.1/summary.json; firmware/emerald/resident.c, firmware/multi-profile/main.c, firmware/sd-video/pico.c; vendor/celio_transport/mb_multi.py.
- [Smeraldo: main e aggiornamenti VBlank](https://github.com/pret/pokeemerald/blob/master/src/main.c).
- [Smeraldo: code di copie sprite](https://github.com/pret/pokeemerald/blob/master/src/sprite.c).
- [Smeraldo: registri grafici buffered](https://github.com/pret/pokeemerald/blob/master/src/gpu_regs.c).
- [Multiboot di riferimento](https://github.com/afska/gba-link-connection/blob/master/lib/LinkCableMultiboot.hpp).
- [Pico SDK: gestione PIO](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html).
- [TinyUSB: CDC e configurazioni](https://docs.tinyusb.org/en/latest/).
- GBATEK, copia consultata in analisi/fonti/gbatek.html: CPU sospesa durante trasferimenti DMA.
