**GBMirroring — analisi tecnica e piano d'azione**

Documento del 9 settembre 2026. È un piano di sviluppo fondato sull'esame del materiale disponibile, non una certificazione di un sistema video già funzionante.

**Decisioni concordate**

- Console iniziale: GBA SP, con supporto previsto anche per GBA; giochi GBA. GB/GBC esclusi da questa prima fase.
- Nessuna modifica hardware interna alla console. Sono ammesse piccole modifiche all'adattatore e un altro cavo.
- Un solo multiboot: riconoscimento automatico della cartuccia e profili interni, con compatibilità crescente. Non è richiesto che giochi sconosciuti funzionino senza un profilo.
- Smeraldo e Verde Foglia sono le cartucce disponibili per le prime prove. Il progetto deve essere estensibile oltre Smeraldo.
- Primo risultato utile: schermo completo, anche a pochi fotogrammi al secondo. Audio da definire; in questa proposta viene rinviato.
- Un'app sul PC è accettabile durante lo sviluppo. Risultato finale: adattatore USB autonomo riconosciuto come webcam, utilizzabile nell'app Fotocamera senza un programma che ricostruisca il gioco sul PC.
- Si parte dai file già disponibili, senza dipendere dal recupero dei sorgenti mancanti dall'amico.
- La dimostrazione osservata mostrava Smeraldo su GBA, un adattatore simile e l'app Fotocamera con poco ritardo. Non sono stati osservati avvio, cambio cartuccia, eventuale flashcart o modifiche della console. È evidenza del risultato visibile per quel caso, non della sua architettura o universalità.

**Valutazione di fattibilità**

La strada credibile è un piccolo programma residente sul GBA che esporta lo stato grafico effettivo, un adattatore che lo riceve e ricompone l'immagine, e un'interfaccia USB Video Class. Il gioco continua a essere eseguito sulla cartuccia e sulla CPU del GBA.

Il Link standard non espone il segnale LCD e non consente al Pico di leggere arbitrariamente la memoria della console: occorre codice cooperante sul GBA. Cambiare solo i descrittori USB del Pico può farlo apparire come webcam, ma non crea la sorgente video.

La parte USB ha precedenti concreti su RP2040: Raspberry Pi documenta un esempio UVC e TinyUSB include un esempio video. La parte da dimostrare è la cattura corretta e sufficientemente economica durante i giochi commerciali. Un singolo caricatore con profili è plausibile come percorso di ricerca e sviluppo; non abbiamo ancora dimostrato frame rate, fedeltà completa o compatibilità su hardware. [Esempio Raspberry Pi](https://www.raspberrypi.com/news/real-time-monochrome-camera-input-on-raspberry-pi-pico/), [TinyUSB video_capture](https://github.com/hathach/tinyusb/tree/master/examples/device/video_capture).

**Che cosa è stato esaminato**

L'inventario comprende tutti i 1.332 file di PROGETTO AMICO: 89.511.344 byte. Sono stati calcolati dimensione, categoria e SHA-256 di ogni file; i sorgenti Python applicativi sono stati anche analizzati sintatticamente e indicizzati. L'analisi funzionale si concentra sui componenti del progetto, sui percorsi critici di trasporto e avvio, sulla struttura dei dati e su parti disassemblate del multiboot. Runtime, DLL, immagini e ROM commerciale sono inventariati: non si intende affermare una decompilazione integrale di ogni binario né un collaudo visivo di ogni immagine.

| Gruppo | File | Contenuto e funzione |
|---|---:|---|
| Sorgenti, interfacce e configurazioni applicative | 29 | Python, Lua, HTML, avvii BAT e JSON |
| Cache Python applicativa | 5 | Bytecode compilato |
| Binari GBA, salvataggio e firmware | 5 | Due mbstub, celio.uf2, ROM e salvataggio in MGBA TEST |
| Immagini dell'interfaccia | 4 | Decorazioni e favicon |
| Mappa e relativi asset | 1.125 | JSON, mappe, personaggi e icone |
| Distribuzione mGBA | 71 | Eseguibili, shader, documentazione e licenze |
| Runtime Python e dipendenze | 93 | Python embeddable, PyUSB, libusb e supporto |

Inventario e indice riproducibili: [inventario-file.json](analisi/inventario-file.json), [indice-sorgenti.json](analisi/indice-sorgenti.json), [riepilogo-materiale.json](analisi/riepilogo-materiale.json). Lo script [inventario.py](analisi/inventario.py) legge i materiali e scrive solo nella cartella analisi.

**Ricostruzione del progetto dell'amico**

| Componente | Funzionamento riscontrato | Utilità per GBMirroring |
|---|---|---|
| mb_multi.py | Implementa il protocollo multiboot MultiPlay a 16 bit sopra il passthrough Celio, con rilevamento, handshake, header, cifratura/checksum e verifica delle risposte. Precarica parole per impedire che gli idle del firmware entrino nel trasferimento. | Trasporto iniziale del nostro loader e riferimento per le prove. |
| mbstub.gba | Loader compilato, riconoscimento di Smeraldo italiano, copia del payload nella coda EWRAM e avvio adattato al gioco. | Riferimento da reverse engineering; non è un loader universale già pronto. |
| inject.amico.lua | Incorpora il payload compilato, controlla ROM e prologo di una funzione, scrive in EWRAM e installa un hook nel vettore IRQ. Legge e scrive mailbox attraverso l'API mGBA. | Banco di studio della residenza e dei dati. L'API dell'emulatore ha accessi che il Pico non possiede. |
| usb_link.py | VID/PID 2FE3:000A; comandi/stato sugli endpoint 01/81, dati su 02/82. Lettori dedicati e deframing persistente fra letture. | Gestione robusta USB e diagnosi; il protocollo video richiederà un trasporto diverso o molto più efficiente. |
| protocol.py | Eventi di 12 byte: tipo, direzione, velocità, sequenza, mappa, coordinate, genere e stato avatar. Datagrammi OWL1 con header di 11 byte. Estensioni per stato, scheda e Cable Club. | Idee di framing e versionamento. Non trasporta pixel o uno stato GPU completo. |
| client.py | Ponte USB/TCP verso relay UDP; deduplica, riordino, recupero di passi mancanti, RTT, simulazione di perdite e pubblicazione delle posizioni. | Diagnostica e separazione del trasporto dalla logica. La rete non è necessaria per la webcam locale. |
| club_link.py | Macchina a stati per handshake e riaperture del Cable Club; epoche di sessione, sequenze, storico e ritrasmissioni di blocchi da 64 byte. | Esempio del perché la porta Link deve avere un proprietario definito. |
| finto_club.py | Simula il partner del Cable Club e parte del protocollo Pokémon, fino all'ingresso nella saletta. | Banco di prova del link; non cattura grafica. |
| pannello.py / pannello.html / BAT | Server HTTP locale, processi figli, avvio multiboot e bridge, mutua esclusione sull'adattatore, log e API posizioni. | Esperienza di avvio riutilizzabile concettualmente. |
| mappa.html / mappa/dati.json | Canvas, mappe e asset pregenerati dalla decompilazione; sovrappone posizioni e direzioni ricevute. Il JSON contiene 518 mappe e 4 mondi. | È una mappa ricostruita con asset, non una cattura del framebuffer. |
| MGBA TEST | Script Lua, bridge TCP e relay locale, insieme a mGBA portable e a file ROM/SAV effettivamente presenti. | Confronti e reverse engineering senza iniziare dalle prove sul salvataggio reale. |

Il payload usa il motore del gioco per rappresentare gli altri giocatori: gli eventi remoti guidano personaggi, pose e movimenti. Questo spiega la quantità molto ridotta di dati trasferiti. L'estrazione del video richiede informazioni di ordine di grandezza diverso, soprattutto durante cambi scena.

La cartella mappa contiene i dati generati; manca tools/gen_mappa.py. Nei file analizzati la provenienza operativa è descritta come generazione dalla decompilazione. Non è stato identificato con certezza un separato repository upstream per l'intera mappa: non attribuisco il motore a un progetto esterno non verificato.

**Che cosa rivela il binario multiboot**

Nel loader principale è presente la firma BPEI, benché l'header del programma multiboot riporti BPEE: leggere soltanto l'header porterebbe a una conclusione errata sulla cartuccia supportata. La routine di controllo confronta anche parole a indirizzi ROM specifici, fra cui 0x08085E70.

La copia del payload parte da 0x0203CF80; un secondo stadio viene portato a 0x0203FE00. Nel secondo stadio disassemblato si osservano:

- disabilitazione degli interrupt e inizializzazione degli stack;
- SWI RegisterRamReset con maschera 0xFE, che preserva EWRAM;
- azzeramento manuale della EWRAM precedente al payload;
- installazione iniziale dell'handler del gioco, chiamate a indirizzi ROM fissi e successiva sostituzione del vettore 0x03007FFC con il payload, conservando l'handler originale;
- salto a una continuazione specifica del gioco, 0x080003CF.

Questo è il passaggio determinante: viene riprodotta/adattata una parte dell'avvio del gioco per non cancellare il programma residente. Il normale avvio di Smeraldo include infatti un reset della memoria e la configurazione dei propri handler. Non si tratta di un semplice salto generico alla cartuccia. I nomi di tutte le routine italiane chiamate non sono ancora stati ricostruiti con una tabella simboli verificata.

Evidenza locale: [secondo stadio disassemblato](analisi/mbstub-avvio-disassemblato.txt), [loader Thumb](analisi/mbstub-loader-thumb.txt). Confronto: [avvio pokeemerald](https://github.com/pret/pokeemerald/blob/master/src/main.c), [crt0](https://github.com/pret/pokeemerald/blob/master/src/crt0.s).

Mancano payload/main.c, payload/sio.c, hook.S, linker script, build.ps1, game_syms.h e sorgenti mbstub. Non occorre attendere che vengano recuperati: possiamo ricostruire un loader minimale nostro usando il comportamento osservato. Il costo di reverse engineering va però incluso nel piano.

**Versioni da non confondere**

| Versione multiboot | Byte | Inizio SHA-256 |
|---|---:|---|
| Cartella principale | 11.860 | 2153d32e92c18172 |
| MGBA TEST | 10.700 | 1240148a70edabc2 |
| Sito PassoTile, scaricato il 09/09/2026 | 11.800 | bd1be4316995f3f8 |

Le copie di client.py, protocol.py e usb_link.py in MGBA TEST sono differenti e meno estese; mb_multi.py è identico. Il relay locale di MGBA TEST gestisce gli eventi di movimento, ma non contiene la gestione T_CLUB del protocollo principale. Non bisogna mescolare queste versioni come se fossero equivalenti.

celio.uf2 contiene 302 blocchi UF2, con family ID RP2040 0xe48bff56, intervallo di programmazione 0x10000000–0x10012e00 escluso. Questo identifica formato e destinazione; non prova il commit sorgente del firmware.

**Hardware e Celio**

La scheda indicata contiene Pico, convertitore di livelli BOB-12009 e selezione della tensione. Per il GBA si lavora sul ramo 3,3 V. Lo schema collega segnali Link, non segnali video LCD. La qualità dei fronti attraverso convertitore e cavo va misurata quando si passa a velocità maggiori: il funzionamento attuale a bassa velocità non certifica quello a 2 MHz. [Progetto hardware](https://github.com/agtbaskara/game-boy-pico-link-board).

Il commento F-3 di usb_link.py documenta il problema concreto della vostra scheda: GP4 non cablato e selezione automatica del percorso SD potenzialmente errata con cavo GBC. L'etichetta software “gba” può quindi indicare il percorso elettrico corretto anche usando fisicamente un cavo GBC. Il piano parte dalla continuità dei fili e dai pin effettivi, non dal solo nome commerciale del cavo.

Celio emula localmente le temporizzazioni MultiPlay e inoltra blocchi di protocollo attraverso Internet. La sua robustezza è legata alla conoscenza del protocollo dei giochi: non costituisce un tunnel universale che riproduce qualsiasi segnale Link senza vincoli. [Celio-Firmware](https://github.com/Celio-Link/Celio-Firmware).

Ho esaminato il driver PIO, il programma master, il raw relay, lo strato USB e il servizio client del repository pubblico. Snapshot dei tree: firmware 4aef46a1aff688cc0a68df666858eccb9b5ae291, client 1d712b2849c3cf248c367035cc0222798b0b4162. Le copie dei sorgenti selezionati sono in analisi/fonti.

Il fork usato dal progetto dell'amico documenta modifiche F-1/F-2/F-3/F-4: timing, preservazione delle parole zero e lunghezze, scelta cavo e riavvio. Nel rawRelaySection.cpp pubblico esaminato rimangono filtro degli zeri e invio di buffer da 64 byte. Inoltre i comandi del firmware pubblico corrente non coincidono tutti con quelli attesi dal fork. Non aggiornare alla cieca il Pico pensando che qualunque Celio sia sostituibile al celio.uf2 ricevuto.

Il vecchio percorso Lorenzooone per Gen 3 usa un homebrew multiboot per gli scambi; è coerente con l'esperienza raccontata. Non fornisce da solo il meccanismo di cattura durante l'esecuzione della cartuccia. [Progetto Lorenzooone](https://github.com/Lorenzooone/PokemonGB_Online_Trades_and_Battles#trading-using-gen3-games).

**La versione web PassoTile**

Sono stati scaricati HTML, configurazione, sette JavaScript referenziati, mbstub.gba, script emulatore e pagina mappa pubblicati. Non è stato aperto un collegamento di gioco al relay né è stato flashato un dispositivo.

La migrazione elimina il bridge Python locale nel percorso hardware: device.js usa WebUSB; multiboot.js carica la ROM; sio.js conserva il framing; bridge.js gestisce giocatori ed eventi; club.js gestisce Cable Club; relay.js incapsula OWL1 in messaggi WebSocket binari. app.js coordina interfaccia, avvio e generazione dello script mGBA. La mappa riceve le posizioni via BroadcastChannel; il codice web include anche spettatori e fino a tre avatar remoti sul GBA. [Pagina esaminata](https://gbcatrade.wired-ariel.it/passotile/).

Il codice client descrive un relay WebSocket verso UDP o un backend alternativo, ma il sorgente del server realmente in produzione non è disponibile nel pacchetto. Questa parte resta ricostruita dal contratto del client, non ispezionata sul server.

La versione web non elimina il programma eseguito sul GBA: scarica e trasmette ancora mbstub.gba. Lo script emulatore pubblicato mantiene il profilo BPEI. Il fatto che non occorra scaricare manualmente file non rende universale il payload.

**Le quattro difficoltà reali**

1. **Residenza.** Ogni profilo deve preservare codice, stack e piccoli buffer durante avvio, menu, battaglie, salvataggio e reset. Non esiste una regione EWRAM riservata al nostro programma in tutti i giochi. Il profilo deve identificare revisione e lingua, verificare firme e rifiutare varianti sconosciute prima dell'iniezione.
2. **Stato grafico completo.** In modalità tile la VRAM contiene tessere e mappe, non il fotogramma finale. Servono anche palette, OAM, priorità, scroll, finestre e trasformazioni. Scroll e vari parametri affini sono registri di sola scrittura: un dump indiscriminato degli I/O non li recupera. [GBATEK, mappa I/O e grafica](https://mgba-emu.github.io/gbatek/#gba-io-map).
3. **Coerenza temporale.** Una lettura distribuita su molti frame può mescolare scene diverse. Effetti HBlank, DMA e modifiche per scanline richiedono informazioni aggiuntive. CRC e frame ID rilevano problemi di trasporto, ma non rendono coerente uno snapshot che era già incoerente sul GBA.
4. **Costo di acquisizione e trasferimento.** CPU e RAM appartengono anche al gioco. La cattura deve avere un budget limitato, senza attese USB nel percorso IRQ. Una webcam può ripetere un fotogramma: ciò non aumenta il numero di immagini nuove realmente catturate.

Per i primi due giochi c'è un punto d'appoggio verificato: entrambi i progetti decompilati mantengono sGpuRegBuffer, una copia RAM di 0x60 byte dei registri gestiti dal loro GPU manager. È un candidato per recuperare i valori non leggibili dagli I/O. Va individuato nelle esatte ROM in uso e controllato contro scritture dirette ed effetti scanline; non è automaticamente lo stato di ogni registro in ogni istante. [Smeraldo](https://github.com/pret/pokeemerald/blob/master/src/gpu_regs.c), [Rosso Fuoco/Verde Foglia](https://github.com/pret/pokefirered/blob/master/src/gpu_regs.c).

**Banda: dimensioni e limiti, non promesse di prestazione**

Un fotogramma 240×160 in un contenitore a 16 bit per pixel pesa 76.800 byte. A 30 fps servono 2.304.000 byte/s, cioè 18,432 Mbit/s, prima degli overhead.

| Collegamento/modello | Limite aritmetico | Conseguenza |
|---|---:|---|
| MultiPlay 115.200 bit/s | 14.400 byte/s prima del protocollo | Meno di 0,19 frame RGB16/s anche nel conto ideale; il percorso attuale è molto più lento |
| Normal 256 kHz | 32.000 byte/s di bit utili ideali | Circa 0,42 frame RGB16/s prima di pause e gestione software |
| Normal 2 MHz | 250.000 byte/s di bit utili ideali | Circa 3,26 frame RGB16/s prima di pause e gestione software |
| UVC YUY2 240×160 a 10 fps | 768.000 byte/s di immagini | Candidato per l'USB del prototipo; da verificare con endpoint, stack e host reali |

Il conto a 2 MHz è semplicemente clock/8, non un benchmark. La documentazione GBATEK segnala vincoli di stabilità con fili lunghi e overhead software per ciascuna parola; contiene inoltre una conversione Mbit/KByte incoerente in quel paragrafo, perciò qui si esplicita l'aritmetica anziché trattarla come throughput misurato. La modalità veloce richiede un driver Normal dedicato: cambiare l'intervallo fra parole del MultiPlay esistente non lo trasforma in Normal a 2 MHz. [GBATEK SIO Normal](https://mgba-emu.github.io/gbatek/#sio-normal-mode).

Le note locali parlano di circa 126–226 parole/s in determinate prove. Sono misure storiche riportate nei sorgenti, non replicate qui. A 126 parole/s, con 9 parole per un evento che contiene 12 byte, si arriva a circa 168 byte/s di eventi: il canale attuale è dimensionato per telemetria.

Trasmettere lo stato grafico iniziale completo significa fino a 96 KiB VRAM + 1 KiB palette + 1 KiB OAM, oltre a registri e metadati. La compressione differenziale può aiutare molto su scene stabili, ma non ha un rapporto garantito sui cambi scena.

L'RP2040 dispone di 264 KiB SRAM e USB full-speed. Due frame RGB16, più VRAM, palette e OAM, occuperebbero già 253.952 byte, lasciando soltanto 16 KiB per il resto. Il firmware finale va quindi progettato con rendering per righe, buffer limitati o altra strategia misurata. Non si presume che un renderer completo e tutti i doppi buffer entrino comodamente. [Datasheet RP2040](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf).

**Architettura proposta**

Prima fase: GBA reale → payload residente → Link → Pico → USB dati → renderer sul PC → anteprima e webcam virtuale.

Risultato finale: GBA reale → payload residente → Link → Pico con cache grafica e renderer → USB UVC → Fotocamera.

Il renderer compone lo stato proveniente dalla console. Non deve far girare una seconda partita sul PC né limitarsi a riprodurre coordinate sopra una mappa. Il renderer del PC serve anche come riferimento corretto con cui confrontare il successivo porting sul Pico.

Propongo firmware video separato, inizialmente minimale con Pico SDK, PIO e TinyUSB. Riutilizzeremo concetti e, quando opportuno, codice compatibile con le licenze dei progetti, ma non serve portare nel prototipo webcam tutto il sistema di sessioni Internet di Celio. Dopo il multiboot si può passare da MultiPlay per il caricamento a Normal per i dati, se il cablaggio verificato lo consente.

Nel risultato finale il Pico conserva anche il loader nella propria flash: una procedura locale può caricarlo sul GBA in attesa multiboot. USB può esporre UVC più un'interfaccia di controllo distinta. Su Windows l'interfaccia video deve usare il driver UVC di sistema; l'eventuale WinUSB riguarda solo l'interfaccia di controllo. La vecchia associazione Zadig al dispositivo andrà considerata durante le prove di enumerazione. [Driver UVC Windows](https://learn.microsoft.com/en-us/windows-hardware/drivers/stream/usb-video-class-driver-overview).

**Piano operativo con risultati verificabili**

| Fase | Lavoro | Criterio per procedere |
|---|---|---|
| 0 — Congelare la base | Conservare hash, firmware funzionante e fonti; identificare Pico, versione SP, cavo e lingua/revisione delle due cartucce. | Matrice hardware/software riproducibile e procedura per ripristinare Celio. |
| 1 — Provare la webcam | Firmware Pico UVC con barre di colore e contatore; primo formato candidato 240×160 YUY2 a 5/10 fps. | Fotocamera mostra il contatore, dispositivo stabile per 10 minuti e dopo riapertura; nessun programma di rendering sul PC. Questo prova solo l'uscita USB. |
| 2 — Misurare il Link | Homebrew multiboot diagnostico con dati noti; PIO/DMA sul Pico, gestione SIO sul GBA; provare 256 kHz e poi 2 MHz se il cavo regge. | Almeno 10 MiB trasferiti per configurazione con CRC verificati; misure di byte/s utili, pause, errori e costo CPU. Nessuna cartuccia commerciale necessaria per questo test. |
| 3 — Loader comune | Ricostruire un avvio minimale e due profili distinti, con firme e aree RAM/stack documentate. Trasmettere solo un battito e diagnostica. | Lo stesso file multiboot riconosce entrambe le cartucce; il battito sopravvive alle scene di prova; cartucce non riconosciute vengono rifiutate chiaramente. |
| 4 — Primo schermo corretto | Recuperare stato grafico, incluso buffer registri; ricomporre un'immagine completa nel renderer PC. Per un dump diagnostico iniziale è ammessa una pausa controllata esplicitamente visibile. | Confronto con screenshot mGBA e con schermo reale; corretti sfondo, sprite, testo, palette e scroll. La pausa diagnostica non vale come streaming completato. |
| 5 — Streaming | Cache lato ricevente, blocchi modificati, snapshot coerenti, frame ID, checksum, risincronizzazione e budget per frame. | Immagini nuove dello schermo completo a pochi fps su entrambi i giochi; misurare latenza e rallentamento del gioco, non soltanto gli fps UVC. |
| 6 — Autonomia sul Pico | Portare il renderer già verificato sul microcontrollore, conversione YUY2, gestione memoria e caricamento iniziale dalla flash del Pico. | Fotocamera mostra il GBA senza renderer/helper aperto sul PC; ripartenza dopo scollegamento e prova prolungata. |
| 7 — Estensione | Profili per nuovi titoli e revisioni, test grafici aggiuntivi e ottimizzazioni; audio solo dopo una scelta esplicita dei requisiti. | Ogni gioco ha una voce di compatibilità e scene effettivamente collaudate. Un titolo nuovo non viene dichiarato supportato sulla sola base del codice header. |

Le fasi 1 e 2 sono piccoli esperimenti indipendenti; la fase 3 è il primo controllo decisivo della generalizzazione oltre Smeraldo. Una terza cartuccia con motore diverso da Pokémon sarà necessaria prima di parlare di supporto ampio ai giochi GBA. Il superamento dei primi due Pokémon non dimostra da solo la generalità del loader.

Per ogni profilo: avvio da partita nuova e salvataggio esistente, movimento e scrolling, menu, battaglie/animazioni, fade e cambi scena, uso del salvataggio, soft reset, perdita e ripristino USB. Verifica delle aree riservate e dello stack; confronto del ritmo del gioco con cattura disabilitata. Il primo obiettivo riguarda il solo video locale: l'uso contemporaneo del Link per multiplayer/PassoTile richiede arbitraggio aggiuntivo ed è una decisione separata.

Se a una fase manca il dato fondamentale, si risolve lì: più banda non recupera registri mancanti; più memoria sul Pico non impedisce al gioco di cancellare il payload; ripetere un frame in UVC non dimostra cattura fluida. Se l'RP2040 risultasse insufficiente soltanto nel rendering, si può valutare un microcontrollore più capace sull'adattatore, restando entro il vincolo di non aprire il GBA.

**Verifiche svolte e limiti attuali**

- Inventario con hash completo e parsing dei sorgenti Python applicativi riusciti.
- Confronto delle versioni multiboot e dei principali file duplicati eseguito.
- Struttura UF2 e porzioni di loader ARM/Thumb esaminate senza eseguirle sulla console.
- Autotest già esistente di mb_multi.py eseguito con Python: passano trasferimento simulato, checksum, rilevamento parole spurie, regressione idle, tolleranza del modello alle pause e padding. Il suo caso 5 salta i binari cercati nelle directory di build originali, assenti nel pacchetto: il messaggio finale non significa che quei file siano stati verificati da quel caso.
- Nessun test fisico Link/UVC, nessun flash del Pico e nessuna prova di cattura eseguiti in questa analisi.

Questa prima analisi stabilisce una base concreta e le prove necessarie. Non assegno ancora una durata credibile all'intero progetto: residenza, coerenza grafica e prestazioni reali sono variabili sperimentali. La prossima consegna di sviluppo dovrebbe essere un banco di prova riproducibile per UVC e Link, seguito dal loader a due profili, prima di costruire un'interfaccia definitiva.

**Dettagli ancora da definire durante lo sviluppo**

Modello esatto di Pico; revisione SP; lingue/revisioni delle cartucce; disponibilità di un analizzatore logico; priorità dell'audio e della cattura durante multiplayer; soglia accettabile di latenza/rallentamento quando avremo le prime misure. Nessuno di questi punti richiede di cambiare il piano appena concordato; serviranno per dimensionare e collaudare i prototipi.


Aggiornamento: valutata uscita video diretta e ricostruzione su PC in [OPZIONI-VIDEO](docs/OPZIONI-VIDEO.md). Prosegue il trasporto a cavo fisso con studio offline compressione/delta; nessun accesso diretto al segnale LCD tramite Link.
