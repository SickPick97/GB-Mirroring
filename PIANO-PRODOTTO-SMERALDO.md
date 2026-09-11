# Piano dopo il collaudo integrato 0.6.1

12 settembre 2026. Analisi e progetto, nessuna implementazione. L'utente conferma GBA super fluido con 0.6.1: questa e la nuova baseline da preservare. Obiettivo: circa 10 stati grafici/s nelle scene ordinarie, mantenendo 240x160 e colori, con un firmware e un avvio. Un solo pacchetto candidato e una sessione hardware integrata; non e possibile certificare in anticipo che non servira alcuna correzione successiva.

## Diagnosi verificata

- 886 transazioni valide in 248,678 s: 3,559/s. 446 senza blocchi cambiati: mediana 7 interventi di cattura, media 7,457, 78 byte ciascuna. Anche senza dati nuovi il percorso attende la scansione completa dei 393 blocchi.
- 431 transazioni non-keyframe con cambiamenti: mediana 21 interventi, 4230 byte; media 3650,47 byte. A 10/s sarebbero circa 36,5 kB/s: proiezione sulle catture attuali, non misura a 100 ms. Il limite software di 155 parole per VBlank equivale a circa 18,5 kB/s massimi prima di altri costi. Occorre ridurre byte e lavoro, non solo cambiare il contatore FPS.
- Il codice prepara hash/compressione/patch prima del controllo finale del budget di parole. Quando non entra, ripete la preparazione nel successivo intervento. Il limite temporale controllato prima del blocco non limita automaticamente il tempo di elaborazione del blocco stesso.
- CRC16 dell'header calcolato bit per bit; header da 24 byte anche per riferimenti da 2 byte. Hot path IWRAM limitato a 1536 byte: ogni ottimizzazione richiede bilancio memoria e misura, non spostare tutto indiscriminatamente.
- Un errore invalida tutta la cache: 53 sequenze non presentate, 26,487 s fino al recupero. La coda USB finale non contiene il guasto; non e ancora identificata la causa iniziale.
- Coda USB PC massima 2,75 ms. Ottimizzare PC serve per robustezza e crescita, ma non spiega da solo i limiti osservati. Il parser chiama ancora il renderer in modo sincrono.

## Architettura principale

Separare stato rapido (registri, OAM, palette) e risorse (tile, mappe, grafica nuova). Un nuovo stato non deve aspettare una scansione completa di VRAM: deve aspettare solo le risorse di cui dipende. Cache del ricevitore versionata; commit coerente, piccolo staging sul GBA. Niente predizione del movimento o interpolazione spacciata per cattura.

1. Osservare code di copie e stato grafico tramite punti di aggancio RAM verificati sulla cartuccia italiana, prima che vengano consumati; confermare dopo l'esecuzione originale quali copie siano avvenute. Non leggere sorgenti RAM mutate dopo il loro consumo. La decompilazione inglese e una guida, non una mappa di indirizzi italiani.
2. Copie generate e consumate dentro lo stesso callback, DMA diretti e scritture CPU possono sfuggire all'osservazione. Mantenere confronti selettivi delle regioni attive e scansione di controllo progressiva. In scene non coperte usare il percorso conservativo; non pubblicare stati dichiarati coerenti con risorse mancanti o scadute.
3. Accorpare i cambiamenti intermedi e campionare circa ogni sei refresh (circa 9,95 Hz). Il dato vecchio puo essere sostituito solo se nessuno stato pendente ne dipende. Durata massima delle code e generazioni esplicite.
4. Trasmettere registri modificati, elementi OAM e intervalli palette; mappe a righe/intervalli e tile a granularita utile. Raggruppare piu piccoli comandi sotto un header protetto. RAW, RLE e riferimenti scelti per costo totale CPU+invio, non solo dimensione.
5. Riferimenti a risorse con identita/generazione e controllo integrita. Una sorgente ROM immutabile puo identificare una risorsa dopo il primo trasferimento; un indirizzo RAM non ne identifica il contenuto. Nessuna ROM commerciale richiesta sul PC. Collisioni/evizioni del dizionario non devono associare versioni diverse allo stesso riferimento.

Budget di progetto: 1-1,2 kB medi per nuovo stato nelle scene ordinarie, circa 10-12 kB/s, piu risorse e controllo entro il budget misurato. E un criterio da verificare con tracce identiche, non un guadagno gia dimostrato. Scene con molte nuove risorse possono ridurre temporaneamente la cadenza; non rallentare il gioco per nasconderlo.

## CPU e memoria GBA

- Prenotare il budget prima dell'elaborazione, oppure conservare un pacchetto preparato e la sua generazione per inviarlo dopo. Nessuna ricompressione evitabile, nessuna lettura incoerente tra hash e payload.
- CRC header a tabella compatta o routine ARM misurata; combinare passaggi di copia/checksum quando corretto. Non eliminare l'integrita per guadagnare FPS.
- Scheduler interrompibile con costo massimo per operazione e margine prima della fine del periodo disponibile. Misurare tutte le fasi, incluso END. Il contatore scanline attuale modulo 228 non certifica il tempo CPU; usare strumenti emulati e contatori compatibili con timer/DMA realmente usati dal gioco.
- Il linker attuale lascia poco spazio. Staging, metadati e dizionario devono sostituire strutture esistenti, non aggiungersi senza limite. Verificare stack, occupazione massima e ripristini. Nessuna copia completa da 100 kB sul GBA.
- Conservare routine sender e cablaggio collaudati come base. Migliorie ARM locali solo se misurate. SIO Normal, DMA a forme d'onda e clock piu aggressivi non sono dipendenze della consegna: percorso fisico non validato oppure sottrazione di risorse CPU/DMA al gioco.

## Recupero e integrita

Un pacchetto errato deve invalidare solo risorse/stati dipendenti. Stato rapido periodicamente autosufficiente; definizioni di risorsa identificabili, riferimenti versionati, patch applicate soltanto alla base corretta. Conservare l'ultima immagine completa durante il recupero, con indicazione di stallo.

Prevedere una breve finestra half-duplex per conferme/richieste di risorse sul collegamento esistente, con direzioni dei pin e tempi di rilascio verificati e timeout strettamente limitato. Non presumere che il reverse path del multiboot dimostri gia quello del protocollo GPIO. La verifica entra nel collaudo unico e non richiede inversione del cavo. Se non risponde, usare automaticamente aggiornamenti assoluti e ripristino progressivo con budget limitato; l'aumento FPS non dipende da questo canale.

Obiettivo recupero sotto 1 s per stato rapido o piccola risorsa persa quando la richiesta e disponibile. Per risorse grandi il minimo e byte da ripristinare / banda assegnata: non promettere un secondo per qualunque cambio scena. Non inviare l'intera cache ogni secondo: potrebbe consumare da sola tutta la banda. Riavvio del solo viewer deve recuperare senza nuovo multiboot quando il residente e ancora attivo.

## PC, Pico e qualita

- Separare ricezione, validazione e rendering. Cache aggiornata in ordine; rendering degli stati completi con coda limitata. Scartare una presentazione vecchia non significa scartare le risorse da cui dipende la successiva.
- Parser binario efficiente, riallineamento ai bit mantenuto, limiti a lunghezze/code. Log distinti per CRC payload/header, risorsa mancante, transazione incompleta, overflow e timeout. Conservare una finestra diagnostica intorno al guasto, non soltanto la coda finale.
- Telemetria distingue campioni, immagini effettivamente diverse, immagini presentate, ritardo delle code e stalli. Misurare la latenza completa soltanto con timestamp sincronizzati o riferimento visivo; non dedurla dalla sola coda USB.
- Nuove misure automatiche leggere; scritture log raggruppate. Anteprima senza smoothing involontario, scala intera, fullscreen, errori leggibili, riconnessione e report esportabile.
- Monitorare overflow PIO/DMA, USB e riavvii; mantenere un solo firmware per boot/video. Chiusura viewer o assenza di consumer non deve lasciare pin pilotati o code senza limite.
- Verificare priorita sprite, trasparenze, blending, finestre, affine e palette durante transizioni. Gli effetti scanline richiedono esportazione del buffer/descrittore effettivamente usato; il solo snapshot registri attuale non li riproduce. Implementare quelli verificati per Smeraldo, distinguere casi non coperti.

## Webcam: requisito separato da non confondere con il viewer

Per UVC autonoma il Pico deve ricostruire i pixel. Il renderer mGBA oggi sul PC non puo essere trasferito automaticamente al RP2040. Progetto: compositore grafico dedicato, sviluppato e confrontato prima sul PC usando gli stessi snapshot, poi portato sul Pico. Un core per ricezione/controllo, uno per composizione dove utile; cache grafica e buffer per righe/strisce con generazioni stabili durante la composizione. Nessun doppio framebuffer imposto.

RP2040 ha 264 kB SRAM. Cache circa 100,6 kB + un frame RGB555 76,8 kB = circa 177,4 kB prima di USB, ring, stack e dizionari. Due framebuffer e le strutture attuali non sono una scelta sicura. Riutilizzare memoria delle fasi multiboot/video, dimensionare le code e produrre il formato UVC supportato a strisce. 240x160 a 16 bit e 10 FPS sono 768 kB/s di soli pixel: USB Full Speed richiede verifica del budget isocrono reale e del funzionamento simultaneo CDC. TinyUSB fornisce la base UVC, non il renderer del gioco.

Non fare affidamento su un giro PC -> Pico -> webcam con frame grezzi: il doppio traffico USB puo saturare il bus. Come uscita usabile mentre si certifica il renderer embedded, il viewer puo essere acquisito da OBS e fornire una webcam virtuale. Richiede un'app aperta e non soddisfa l'autonomia finale. Dichiarare esplicitamente quale uscita passa i criteri, senza chiamare completo il requisito UVC prima della sua prova.

Audio e supporto ad altre cartucce restano estensioni: non sono necessari per la richiesta attuale e consumerebbero budget o richiederebbero nuovi profili. Proteggere pero la continuita dell'audio del gioco nei test di fluidita.

## Una consegna e una sessione hardware

Sviluppo interno: tracce comparabili statico/cammino/dialoghi/menu/centro/battaglia; prove residente ARM e memoria; decoder con perdite, bitshift, restart e riferimenti fuori ordine; confronto renderer; avvio portatile reale da cartelle con spazi. Non spedire versioni intermedie per ciascuna misura. Fermare una variante che peggiora il gameplay nei test interni.

Consegna: un UF2, un loader, un avvio guidato, report automatico, versioni e hash espliciti, ritorno alla baseline disponibile nello stesso pacchetto. La configurazione normale viene scelta sul software verificato; un fallimento della modalita rapida viene registrato e segnalato, non mascherato come successo a 10 FPS.

Collaudo utente unico guidato di circa 10-15 minuti: avvio, cammino, dialogo, menu squadra, entrata/uscita Centro, battaglia, pausa/ripresa e riapertura viewer; webcam se pronta. Rapporti per fase e confronto cattura attiva/in pausa, senza cambiare UF2 durante la sessione.

Criteri: circa 10 stati/s sostenuti nelle scene ordinarie con variazione reale quando la scena cambia; gioco e audio comparabili alla baseline; nessuno stallo persistente; recupero misurato; code limitate e ritardo ordinario obiettivo sotto 0,5-1 s. Transizioni e scene particolari riportate separatamente. UVC autonoma accettata solo con viewer chiuso e immagine reale in Fotocamera. Nessuna promessa di perfezione in ogni scena prima del collaudo.

## Fonti consultate

- Codice e rapporti locali 0.6.1, in particolare resident.c, fast.S, resident.ld, graphics_stream.py, graphics_renderer.py.
- https://github.com/pret/pokeemerald/blob/master/src/main.c
- https://github.com/pret/pokeemerald/blob/master/src/dma3_manager.c
- https://github.com/pret/pokeemerald/blob/master/src/sprite.c
- https://github.com/pret/pokeemerald/blob/master/src/gpu_regs.c
- https://github.com/pret/pokeemerald/blob/master/src/scanline_effect.c
- https://www.raspberrypi.com/products/rp2040/
- https://github.com/hathach/tinyusb/tree/master/examples/device/video_capture
