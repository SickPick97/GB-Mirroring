# Da 0.8.0 a uno streaming regolare da circa 30 a 60 FPS

12 settembre 2026. Solo analisi e piano: nessun nuovo software, firmware o binario. Target Smeraldo italiano originale, GBA SP, RP2040 e cavo attuale. L'utente conferma scatti solo sul PC, accetta 150-250 ms di ritardo e preparazione automatica di una cache grafica locale. La pagina web resta l'uscita definitiva.

## 1. Cosa dimostra il test

Evidenza selezionata: test-results/2026-09-12-emerald-v0.8.0. Una sessione con piu fasi, non piu prove indipendenti.

| Misura | Risultato |
|---|---:|
| Transazioni verificate consecutive | 3119, sequenze 0..3118 |
| Intervallo fra primo e ultimo arrivo | 303,9726 s |
| Frequenza media | 10,2575 FPS |
| Immagini effettivamente cambiate | 1807 |
| Intervallo mediano / p95 / p99 | 60,1 / 228,2 / 513,8 ms |
| CRC errati, header errati, recuperi, salti | tutti zero |
| Keyframe completi | 11 |
| Picco rendering PC / coda USB | 32,76 / 11,44 ms |

L'etichetta cammino misura 4,99 FPS; menu 14,68; centro 9,38; battaglia 8,81. Sono finestre segnate manualmente: non certificano che ogni intervallo contenga soltanto quella scena. La parte iniziale non e etichettata. Non nascondere le transizioni calcolando solo i periodi facili.

Il gap massimo di 8,314 s comprende circa 5,8 s prima dell'inizio della successiva cattura e circa 2,5 s per il relativo keyframe. Il log non identifica da solo pausa manuale o cambio callback: non attribuirlo interamente al trasporto. Differenza fra intervalli degli END GBA e arrivi PC: mediana -2,89 ms, p95 +13,01 ms. Gran parte dell'irregolarita e dunque gia presente prima dell'arrivo PC. Il browser puo aggiungerne altra: manca la sua telemetria di presentazione.

Il codice impone almeno tre VBlank fra avvii: massimo nominale 59,7275/3 = 19,91 catture/s. Una transazione attende inoltre tutte le risorse e puo durare molti VBlank. Anche 609 transazioni senza modifiche hanno mediana due interventi, p95 undici, pur inviando soltanto 78 byte. Aumentare il polling del browser non risolve questi limiti.

I contatori degli END avanzano a circa 59,729/s nella sessione; coerenti con il clock nominale, ma non prova autonoma di fluidita del gameplay. La conferma della console fluida viene dall'utente.

## 2. Decisione architetturale

Conservare il collegamento GPIO/PIO funzionante. Sostituire la transazione globale con un flusso di stati grafici piccoli e risorse versionate. Il PC ricostruisce esclusivamente lo stato osservato sul GBA: non esegue una seconda partita e non inventa movimenti.

Tre percorsi coordinati:

1. **Stato rapido:** variazioni OAM, scorrimento, registri, matrici affini e palette necessarie. Campionamento in un punto definito dopo gli aggiornamenti grafici del gioco; timestamp VBlank e generazione di scena. Raccolta ogni VBlank quando sostenibile, profilo iniziale ogni due VBlank.
2. **Risorse:** tile, mappe, immagini nuove, patch e operazioni di copia/riempimento. Invio una volta, poi riferimenti. Priorita alle risorse richieste da un prossimo stato visibile; audit di sicurezza a budget inferiore.
3. **Presentazione:** stato pubblicabile solo quando tutte le sue dipendenze sono disponibili nella versione corretta. La grafica di una scena nuova non si mescola arbitrariamente con quella precedente. Un aggiornamento indipendente non deve aspettare l'audit di tutta VRAM.

Il vecchio piano prevedeva gia questa separazione; le release finora hanno introdotto ottimizzazioni e osservatori, ma il commit del frame e rimasto globale. Questa e la parte strutturale ancora da realizzare.

Non basta mandare le coordinate del personaggio: servono anche altri sprite, animazioni, priorita, finestre, palette e mutazioni delle mappe. Non basta pubblicare la cache dopo ogni pacchetto: produrrebbe stati misti e falsi FPS.

## 3. Osservazione corretta del gioco e memoria

Usare le code e i callback RAM verificati del profilo BPEI. PRET documenta buffer registri, richieste DMA e copie sprite, utili per conoscere destinazione, dimensione e natura del cambiamento. Quei sorgenti sono prevalentemente inglesi: indirizzi e comportamento vanno confrontati con la cartuccia italiana, senza trasferire indirizzi alla cieca.

Una richiesta presente prima dell'IRQ non e necessariamente gia eseguita dopo: il gestore DMA puo rinviare lavoro per tempo o volume. Il protocollo deve registrare copie effettivamente completate, con ordine e generazioni. Le sorgenti RAM possono cambiare prima dell'invio: conservare un puntatore non equivale a conservare i dati. Occorre uno staging piccolo e immutabile o rilettura/versionamento con rifiuto dello stato incoerente. Le scritture fuori dalle code richiedono audit e profili specifici. Non assumere che si possano modificare funzioni nella ROM originale.

La build attuale termina a 0x0203f640, prima dello stack a 0x0203f800: restano solo 448 byte nella regione riservata. Nessuna grande cache aggiuntiva sul GBA. Prima del nuovo residente: bilancio esplicito di codice, hash, snapshot rapido, staging, metadati e stack; riuso delle strutture attuali e code limitate. Cache grande e cronologia stanno sul PC; eventuale lavoro Pico usa memoria riutilizzata fra boot e video. Estendere le aree GBA e ammesso soltanto dopo verifica per tutti i callback interessati, senza sovrapporsi a heap o salvataggi.

## 4. Cache automatica dalla cartuccia

Preparazione prima di avviare la partita: leggere dal GBA solo le risorse ROM necessarie, identificarle per profilo e contenuto, verificarle e salvarle localmente. Progressi, ripresa e riuso agli avvii successivi. Nessuna ROM da scaricare o contenuto commerciale incluso nella repository. Prima lettura con homebrew dedicato, senza imporre al gioco il costo del trasferimento iniziale.

Quando una copia proviene da una regione ROM nota basta un riferimento. Per grafica decompressa in RAM, l'indirizzo ROM originario puo essere perso: occorrono corrispondenze verificate tramite contenuto o metadati disponibili, non supposizioni. Dati generati, testi, palette dinamiche e cambiamenti non riconosciuti continuano come patch reali. Le impronte usate come identita richiedono controllo di collisione/validazione; la cache non puo rendere invisibili errori.

Cache anche delle scene visitate, senza invalidazione globale entrando in menu. Prefetch soltanto da dati osservati o tabelle verificate. Nessuna promessa di preparazione in pochi secondi: durata = byte selezionati / banda iniziale misurata. Non rendere obbligatorio il trasferimento dell'intera ROM se bastano risorse selezionate.

## 5. Budget: come decidere se 30 o quasi 60 sono sostenibili

Il limite corrente di 155 parole/intervento equivale al massimo teorico di 18,52 kB/s se usato a ogni VBlank. Non e banda garantita: scansione, codec, attese e margine CPU riducono il dato utile. A 30 stati/s sono circa 617 byte totali per stato; a 50 circa 370, includendo risorse, header e recuperi. Nell'attuale sessione gli header stimati pesano il 25,7% dei byte dei frame verificati.

Obiettivo di progetto per il percorso rapido: normalmente 80-160 byte per stato, header compreso, tramite delta degli attributi realmente cambiati e comandi raggruppati. A 50/s sarebbero 4-8 kB/s, piu risorse. E un budget da verificare, non una misura gia ottenuta. Non basta che la media entri: servono margine e analisi dei picchi delle scene complesse.

Pacchetti con piu comandi e un solo CRC; sequenze, generazioni e ripristino per risorsa. Quota riservata agli stati rapidi e quota alle risorse, con priorita e controllo degli overflow. Se una risorsa obbligatoria non entra, lo stato non puo essere dichiarato completo. Non contare repliche o immagini interpolate come nuove catture.

Limite CPU in cicli/tempo, non solo parole: evitare elaborazioni ripetute di un pacchetto che non entra nel budget. Preparazione incrementale con stato di avanzamento. Misurare prima/dopo IRQ e tempi delle sottosezioni; non usare peak_work_scanlines come tempo CPU assoluto, perche e modulo 228 e incompleto. Nessun timer/DMA del gioco riutilizzato senza analisi delle interferenze audio/scanline. Non raddoppiare alla cieca il budget di invio.

Due profili naturali: circa 29,86 stati/s (un campione ogni due VBlank) e circa 59,73 (ogni VBlank). 50 non divide regolarmente il clock del GBA: e meglio progettare per quei due profili, usando 50+ come obiettivo prestazionale del percorso rapido, senza introdurre un campionamento irregolare deliberato.

## 6. Renderer PC e browser

Il renderer attuale ripristina uno stato mGBA e simula due frame homebrew per ogni immagine, poi converte i pixel con un ciclo Python. Picco misurato 32,76 ms: non e la media, ma lascia poco margine per 30 FPS e supera i 20 ms disponibili a 50.

Preparare una piccola libreria nativa che usi direttamente il renderer GBA di mGBA, aggiornando VRAM/OAM/palette/registri senza simulare CPU e audio per due frame a ogni immagine. Versione fissata, licenza e sorgenti delle modifiche inclusi secondo i requisiti. Conversione pixel in blocco; cache nativa persistente con dirty flags, prove di confronto per sprite, blending, finestre, affine, mosaic e scene particolari. Obiettivo interno p95 sotto 8-10 ms sul PC di riferimento. Non presumere che le funzioni siano gia esportate dalla DLL libretro corrente.

Acquisire i descrittori/buffer degli effetti per scanline di Smeraldo ove verificati: uno snapshot dei registri a inizio frame non basta per ogni effetto di battaglia. Percorso conservativo esplicito per casi non coperti; non chiamare equivalente al GBA un renderer che li omette.

WebSocket binario locale, invio su nuovo stato e coda limitata; risorse affidabili e ordinate, presentazioni superate scartabili. Sostituire fetch + setTimeout(20) con ricezione separata e disegno sincronizzato a requestAnimationFrame. Buffer iniziale di circa 200 ms, adattabile 150-250, basato sul timestamp GBA e una stima stabile del clock. I frame restano ordinati nel tempo; il buffer non e una semplice attesa aggiunta a ogni richiesta. Se i dati arrivano troppo lentamente non li crea: segnala ritardo e conserva l'ultimo stato valido.

Misurare acquisizione, invio, ricezione, commit, rendering e presentazione browser. Contatori distinti: campioni coerenti, immagini cambiate, immagini mostrate, ritardo, duplicazioni, underrun e scarti. Un monitor a 60 Hz non prova 60 stati dal GBA. Gestire pausa, tab nascosta, fullscreen, vista OBS e ripresa senza accumulare secondi di arretrato.

## 7. Alternative considerate

| Strada | Decisione |
|---|---|
| Solo ridurre 3 VBlank a 1 | Rimuove un tetto, non il costo per risorsa e il blocco globale: insufficiente. |
| Solo buffering/WebSocket | Migliora regolarita e percorso PC, ma non genera dati mancanti. Parte necessaria, non soluzione completa. |
| H.264/AV1/WebRTC dei pixel | Interviene dopo il collo di bottiglia GBA-Link; non risolve la cattura. |
| Frame interpolation / predizione | Puo sembrare fluida, ma inventa stati e puo alterare pixel art, menu e occlusioni. Non base del prodotto richiesto. |
| Seconda partita emulata con soli input | Sincronizzazione di timer/RNG/interrupt e salvataggio non garantita; non equivalente al video dell'hardware. |
| SIO normale a 2 MHz | Solo alternativa sperimentale se necessario: instradamento sul cavo fisso non verificato in quella direzione, prove precedenti negative. Non fondare il piano sul bitrate nominale. |
| DMA verso GPIO | Non da automaticamente trasporto gratuito: contende/ferma CPU e i trigger non sono un generico motore seriale. Rischi audio e temporizzazione da valutare prima. |
| Segnale LCD diretto | Non disponibile sulla porta Link; richiederebbe un altro percorso hardware, escluso dal requisito. |

## 8. Sviluppo e condizioni di consegna

Un'unica futura consegna integrata, con tutte le prove interne prima. Non altre release per cambiare soltanto un parametro.

1. Tracce coerenti in emulazione per cammino, dialoghi, squadra, menu, centro e battaglie: quantificare byte minimi di stati/dipendenze, copertura osservatori e memoria. Confrontare il costo dei nuovi hook con la baseline. Se il budget non torna gia qui, rivedere il disegno prima del firmware finale.
2. Renderer diretto, ricezione, buffering e temporizzazione browser con riproduzione delle stesse tracce. Dimostrare correttezza grafica e margine CPU, separatamente dagli FPS del monitor.
3. Cache iniziale automatica, protocollo a risorse versionate e nuovo residente entro le aree sicure; recupero selettivo. Pico unificato aggiornato solo se richiesto dal nuovo controllo; un solo flash eventuale, nessun cambio durante la sessione. Conservare avvio 0.8.0 come confronto.
4. Collaudo integrato di 10-15 minuti sul GBA dell'utente, una sola sessione con scene guidate, acquisizione browser e confronto con cattura in pausa. Automatica raccolta delle misure; nessuna compilazione o cache manuale per l'utente.

Accettazione minima: circa 30 stati coerenti/s sostenuti nelle scene normali, ritmo di presentazione regolare e ritardo di riproduzione 150-250 ms quando la produzione lo consente; gioco e audio sul GBA indistinguibili dalla baseline per l'utente, senza incremento misurabile dei frame gioco mancati. Obiettivo superiore: 50+ stati/s dove il budget consente acquisizione a ogni VBlank. Riportare separatamente finestre di un secondo, percentili degli intervalli, minimo per scena, attese da dipendenze e transizioni: una media globale alta non certifica il minimo richiesto.

Per il profilo circa 30, obiettivo di presentazione p95 vicino a 33,5 ms e p99 sotto 50 ms nelle scene senza caricamento; nessun congelamento nascosto da frame ripetuti. Le transizioni devono avere durata aggiunta misurata rispetto al GBA. Una scena che resta sotto il minimo e una limitazione aperta, non un successo da escludere dal rapporto.

Questa e la strada con la migliore corrispondenza ai colli di bottiglia osservati. Non c'e ancora una dimostrazione di 30-50 FPS in tutte le scene sul cavo reale. La soluzione puo essere progettata e verificata progressivamente; definirla gia definitiva e garantita senza quelle prove sarebbe scorretto.

## Fonti e base tecnica

- Codice locale 0.8.0: resident.c, resident.ld/map, graphics_stream.py, graphics_renderer.py, mgba_headless.py, sd_video_viewer.py, win_serial.py e firmware/unified/pico.c; report originale e selezione ripulita indicata sopra.
- [Temporizzazione video mGBA](https://github.com/mgba-emu/mgba/blob/master/include/mgba/internal/gba/video.h): 280896 cicli per frame e strutture video.
- [Renderer software GBA mGBA](https://github.com/mgba-emu/mgba/blob/master/src/gba/renderers/video-software.c): interfacce registri/memorie e rendering scanline, base da integrare e verificare.
- PRET: [main/IRQ](https://github.com/pret/pokeemerald/blob/master/src/main.c), [DMA](https://github.com/pret/pokeemerald/blob/master/src/dma3_manager.c), [registri](https://github.com/pret/pokeemerald/blob/master/src/gpu_regs.c), [sprite](https://github.com/pret/pokeemerald/blob/master/src/sprite.c), [scanline](https://github.com/pret/pokeemerald/blob/master/src/scanline_effect.c). Riferimenti strutturali, non indirizzi italiani gia certificati.
- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame): sincronizzazione al repaint e comportamento dei tab nascosti.
