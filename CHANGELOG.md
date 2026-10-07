# Storico

## 0.14.1 con Pico 0.8.1 - Slot di controllo: non piu a ogni frame, e mai sopra i pacchetti

- **Richiede il firmware Pico 0.8.1** (`dist/gbmirroring-unified-v0.8.1.uf2`).
- Risultato hardware 0.14.0 + Pico 0.8.0 con il registro di tutti i pacchetti (log-20261007-152655, riepilogo in test-results/hardware-v0.14.0b): 4 s di ritardo entrando in una struttura; correndo nei percorsi lo streaming rallenta fino a fermarsi. Sul GBA il gioco non rallenta.
- Causa 1 (riprodotta nell emulatore con il residente iniettato): durante un caricamento lo slot di controllo veniva eseguito nel tempo libero di ogni frame; i suoi quasi trenta righe non lasciavano spazio ad altro e per decine di frame partiva il solo tick. Nel log: dopo l ingresso 30 frame con il gioco occupato (inevitabili) e poi circa 100 frame con tick da 19-46 parole e nessun pacchetto nel tempo libero. Ora lo slot gira nel tempo libero ogni 30 frame, ogni 8 durante un caricamento, e solo con almeno 60 righe davanti; non gira piu dentro il tick. Emulatore, stesso ingresso: blocchi in sospeso esauriti circa 40 frame prima (senza Pico, quindi senza annunci).
- Causa 2 (Pico 0.8.0): una risposta armata in ritardo restava in attesa per 5 ms di un SC alto lungo; quello successivo e un pacchetto messo in pausa da un interrupt del gioco, e i 450 bit della risposta venivano scritti sopra i pacchetti. Nel log: pacchetti persi (salti di sequenza di 5 e 283 pacchetti, 3,75 s senza dati validi), 4 richieste di risincronizzazione in 50 s e fotogrammi chiave a catena: il blocco nei percorsi. Pico 0.8.1: nessuna risposta se dopo END sono gia arrivate altre parole, e risposta ritirata se non inizia entro 500 us.
- Richieste di copia ROM osservate per VBlank da 5 a 4 (le conferme erano gia 4) per fare posto in RAM.
- Non ancora provata su console.

## 0.14.0 (aggiornamento solo PC, nessun binario nuovo) - Registro di tutti i pacchetti

- Risultato hardware 0.14.0 con Pico 0.8.0 (log-20261006-230154, riepilogo in test-results/hardware-v0.14.0): per l utente non e cambiato nulla, stessi problemi nei caricamenti.
- Dal log: il canale di ritorno funziona sull hardware (19 slot su 19 nella coda USB portano un verdetto valido, i due bit storici sono corretti) e, nella parte visibile, gli annunci vengono risolti in pochi tick. Ma a ogni cambio di scena la pagina resta in attesa 2,4-3,6 s (0.13.2: circa 2 s; 0.13.0: 1,0-1,8 s) e il registro contiene solo i frame pubblicati: i tick ricevuti e poi scartati durante l attesa non compaiono, quindi non si vede che cosa il GBA manda in quei secondi. Solo 16 annunci risultano nei frame pubblicati.
- Nuovo file `pacchetti.jsonl` nel log scaricato: una riga per ogni pacchetto ricevuto (tick e tempo libero), anche quelli scartati dall attesa, con blocchi in sospeso, annunciati, in attesa, parole, codec, righe usate e tempo libero.
- La memoria dei blocchi visti viene salvata ogni 30 s (prima solo alla chiusura ordinata, che di fatto non avveniva: il file non era mai stato creato).

## 0.14.0 - Caricamenti: blocchi annunciati per firma e risposta del PC (Pico 0.8.0)

- **Richiede il firmware Pico 0.8.0** (`dist/gbmirroring-unified-v0.8.0.uf2`). Con il Pico 0.7.0 il residente 0.14.0 funziona ma senza la risposta del PC; il Pico 0.8.0 resta compatibile con i residenti precedenti.
- Risultato hardware 0.13.2 (log-20261006-151923 e osservazione diretta della pagina, riepilogo in test-results/hardware-v0.13.2): camminando tra due zone compaiono pezzi di sentiero bianchi e "Caricamento scena"; entrando in un edificio nero per circa 4 s (stream a 21 fps), poi interno con piastrelle sbagliate e righe magenta; all inizio di Surf lo sfondo e una piastrella ripetuta.
- Causa misurata nel log: a ogni caricamento il gioco cambia 350-390 blocchi di VRAM e il collegamento ne porta circa due per frame (un blocco non compresso sono 130 parole), quindi servono secondi; allo scadere dell attesa la pagina mostrava l immagine incompleta (44 rilasci forzati in 517 s). Il tempo libero del GBA non manca (mediana 82 righe).
- Record 14 (annuncio): quando ci sono almeno 48 blocchi cambiati in sospeso (un caricamento) il residente manda per ciascuno prima solo la firma (4 parole). Il PC ricostruisce subito il blocco se conosce quel contenuto: lo ha gia visto (anche in sessioni precedenti: `runtime/cache/blocchi-visti.bin`, locale e non versionato) oppure lo trova nella grafica compressa della cartuccia, indicizzata all avvio dalla copia ROM locale (`tools/rom_blocks.py`: 2572 flussi LZ77, 135.604 blocchi, circa 4 s in secondo piano). Con meno blocchi in sospeso (una posa, una casella di testo, un passo di scorrimento) tutto va come nella 0.13.2.
- Risposta del PC (verdetto): il PC manda al Pico, e il Pico al GBA nello slot di controllo, il numero di sequenza letto e un bit per blocco "questo contenuto lo conosco". Il residente lo chiede nel tempo libero quando ci sono annunci in sospeso; ai blocchi conosciuti restituisce la firma e non ne manda il contenuto, cosi restano da spedire solo quelli che al PC mancano. La pagina aspetta solo i blocchi annunciati che non conosce.
- Pico 0.8.0: lo slot di controllo passa da 2 bit a 2 + 448 bit, alimentato via DMA, con rilascio della linea alla fine; il verdetto scade dopo 200 ms; senza verdetto valido la risposta e a tutti uno e il residente la scarta (parola di controllo). Nuovo comando seriale `V` + 112 cifre esadecimali.
- Errori trovati e corretti durante lo sviluppo, tutti coperti da test: conteggio dei blocchi in sospeso sottratto due volte, blocco tornato al contenuto precedente che restava sbagliato sul PC, annunci che spostavano il giro di invio oltre la mappa di scorrimento.
- Per fare posto in RAM: tolti il dizionario interno di 64 contenuti (lo sostituisce la memoria del PC) e la cadenza ridotta SELECT+R+A; il campo fisso del pacchetto ha una parola in piu (blocchi annunciati in sospeso). EWRAM del residente piena.
- Co-simulazione (non hardware) rispetto alla 0.13.2: corsa 289/299 frame identici (295/299), lotta 678/687 (666/683), Surf 341/342 (343/344), ingresso nel Centro Pokemon 749/818 (713/808).
- Compilazione del Pico su questa macchina: dipendenze fissate riscaricate con `tools/prepare_dependencies.py` (hash verificati); CMake di MSYS con Makefile al posto di Ninja.
- Non ancora provata su console: slot esteso e tempi sul cavo verificati solo con il modello PIO e il codice ARM del residente in emulazione.

## 0.13.2 - Riproduzione senza accumulo di ritardo, blocchi noti per primi, dissolvenze complete

- Risultato hardware 0.13.1 (log-20261002-174228, riepilogo in test-results/hardware-v0.13.1): in esplorazione scatta di piu e nelle lotte e nelle case ci sono piu glitch. Il log del PC mostra 14 azzeramenti della coda del browser in 87 s (0.13.0: 9 in 378 s), 48,6 fps nel browser e, nel campo, 24 rilasci forzati: durante la camminata continua i 24 blocchi mappa di ogni passo di scorrimento restavano in attesa per 7 tick su 8, la pagina tratteneva l immagine fino a 31 frame e poi la mostrava tutta insieme.
- Browser (`playout.js`): il recupero del ritardo della 0.13.1 accumulava uno sfasamento permanente (608 ms su quel log) e provocava azzeramenti. Ora i frame arrivati in ritardo in blocco (dissolvenze dopo un caricamento) vengono mostrati in ordine, qualche frame in piu per aggiornamento finche il ritardo e rientrato, senza scartare la coda; l azzeramento scatta solo oltre 3 s di ritardo. Simulato sul log: 4673 frame mostrati su 4765 e 3 azzeramenti (la riproduzione della 0.13.0 mostrava 1041 frame su 4765 su quel log).
- Residente: i blocchi noti come modificati (copie in coda del gioco, scorrimento della mappa) vengono inviati per primi; i blocchi solo in verifica (audit a rotazione, tile degli sprite visibili) usano il tempo rimasto. Prima la verifica di molti blocchi sprite ritardava i 24 blocchi mappa di un passo di scorrimento. Il tick non usa piu meta del tempo libero del frame precedente (era 33,5 contro 29,4 righe di media nel campo in co-simulazione).
- La modalita "tick pesante" (poche righe) scatta solo se il gioco e occupato al VBlank, il suo gestore finisce tardi o il tempo libero misurato e basso; la mancanza di un controllo di tempo libero non basta piu. Nuova telemetria nel log: tempo libero misurato (`idle_slack`) e tick pesanti (`heavy_tick`).
- Dissolvenze: durante un caricamento le copie di tile dalla ROM arrivate dopo entrano in tutti i frame trattenuti (prima la dissolvenza mostrava la scena vecchia con la palette nuova); durante la camminata ogni frame trattenuto conserva la propria posa degli sprite.
- Il residente occupa 7756 byte, EWRAM quasi piena (20 byte liberi); carico utile massimo 216 parole, 5 richieste ROM per VBlank.
- Non ancora provata su console; firmware Pico invariato (0.7.0).

## 0.13.1 - Battaglie senza scatti, effetti per riga, animazioni e dissolvenze

- Risultato hardware 0.13.0 (log-20260930-184140, riepilogo in test-results/hardware-v0.13.0): "funziona divinamente", restano glitch qua e la: animazioni di corsa a volte sbagliate, mosse come Surf non corrette, cambi mappa e ingresso in battaglia con schermo nero invece della transizione, barra HP che scende a scatti.
- Battaglia a scatti: il 70% dei salti di frame era in battaglia, dove il gioco a volte e ancora occupato al VBlank o il suo gestore finisce dopo la riga 224; il residente saltava il tick. Ora in quei frame manda comunque registri, palette e OAM entro poche righe; salta tre tick su quattro solo in un lungo periodo occupato (salvataggio, caricamenti). Gioco emulato in battaglia: 900 tick su 900 (prima 845).
- Barra HP e sprite ridisegnati sul posto: nel tempo libero, ogni frame, vengono verificati i tile di tutti gli sprite visibili (dalla OAM), non solo a rotazione.
- Animazioni di corsa: un frame trattenuto dal PC usava la VRAM piu recente, quindi la posa successiva dello sprite (copiata dalla ROM nel tick dopo) compariva nella posizione precedente. Ogni frame trattenuto ora ha la propria copia della VRAM, completata solo dai blocchi inviati come contenuto (19% dei frame del campo era trattenuto nella prova hardware).
- Effetti per riga: il residente legge `gScanlineEffect` (0x02039b28 in BPEI) e invia la tabella per riga (record tipo 13) quando cambia; il renderer nativo applica il registro riga per riga (`gbm_render_lines`). Intro della battaglia nel gioco emulato: 0 pixel sbagliati su 183 frame (senza: 586.996). Le transizioni che programmano il DMA da sole non sono ancora riprodotte (un tentativo euristico peggiorava l immagine ed e stato tolto).
- Renderer ricompilato con Zig 0.16.0 (clang, statico; scaricato con permesso, sha256 verificato): pixel identici alla DLL MSVC precedente su 120 frame.
- Cambi scena: il PC riproduce gli ultimi frame trattenuti (fino a 40, i neri del caricamento ridotti a uno) cosi la dissolvenza della nuova scena si vede; il browser recupera poi il ritardo riproducendo un po piu veloce. La verifica completa della VRAM non riparte piu quando il gioco resta senza callback VBlank durante il caricamento; il tick usa fino a meta del tempo libero del frame precedente (max 60 righe) e il lavoro nel tempo libero arriva alla riga 156.
- RAM: lo stage di avvio del loader ora gira dentro la tabella delle firme del residente (azzerata al primo keyframe), liberando 256 byte; code di copia ROM 6 richieste, 4 conferme per tick; contatori di debug solo nelle build di sviluppo.
- La statistica "salti di sequenza" della pagina conta solo le perdite reali (i pacchetti del tempo libero non generano immagini).
- Salvataggio: `test_save_integrity.py` passa (flash identica al gioco senza residente, salvo il tempo di gioco; checksum valido). Non provata su console; firmware Pico invariato (0.7.0).

## 0.13.0 - Tempo libero del gioco, interrupt mai bloccati, firma dei blocchi corretta

- Richiesta dopo la prova hardware 0.12.3: la battaglia non crasha piu ma resta un fermo immagine; entrando nelle case, nelle informazioni dei Pokemon e nei menu molti glitch grafici. Obiettivo: uno streaming come il gioco vero, senza toccare il salvataggio.
- Firma dei blocchi (causa dei glitch persistenti nei menu, presente anche in 0.12): la parte xor-rotazione di `hash_begin` ignorava le parole a tinta unita (0x11111111 ruotata si annulla) e, ripetendosi ogni 32 parole, non distingueva le due meta di un blocco scambiate; il GBA credeva che il PC avesse gia quel contenuto e non lo reinviava, e il tile sbagliato restava a schermo per decine di frame (riprodotto nella co-simulazione alla chiusura del Pokedex e con una riga vuota in un blocco a tinta unita). Ora la prima firma e una catena moltiplicativa (FNV-1a su parole) e dopo ogni gruppo di otto parole entrambe vengono rimescolate; il PC usa la stessa funzione (`stream_hash`), verificata contro il codice ARM (`test_block_hash.py`).
- Tempo libero: Smeraldo non ferma la CPU in attesa del VBlank, gira nel ciclo `WaitForVBlank` (0x080008c6). Il timer 1 (fermo durante il gioco, voce vuota nella tabella interrupt) controlla ogni dieci righe se il gioco e in quel ciclo con il flag VBlank spento; allora il residente legge le code di copia e invia i blocchi in attesa (nuovo pacchetto tipo 13) e verifica il resto della VRAM, fino alla riga 150, iniziando un blocco solo se c e il tempo di finirlo (costo misurato in mGBA: circa sei parole per riga).
- Interrupt mai bloccati: tick e lavoro nel tempo libero girano in modalita di sistema con gli interrupt abilitati. Prima del gestore del gioco il residente esegue un solo confronto. Via la modalita corta della 0.12.2/0.12.3 che nelle scene sconosciute (battaglia) riduceva i tick quasi a zero: era la causa del fermo immagine.
- Controllo "gioco occupato" corretto: usa l indirizzo interrotto salvato dal BIOS (prima leggeva l indirizzo di ritorno nel BIOS e non scattava mai). Con il gioco occupato (salvataggio, caricamenti) il residente salta fino a sette tick e non controlla il tempo libero; nei frame pesanti il tick e limitato dal tempo che il gioco ha lasciato libero nel frame precedente.
- Dopo un cambio scena tutti i blocchi non verificati contano come in attesa: il PC tiene l ultima immagine completa (la pagina mostra "Caricamento scena...") invece di mescolare tile vecchi e nuovi; dopo un attesa lunga mostra solo l ultimo frame completo. Le copie osservate prima del VBlank vengono applicate solo dopo il VBlank. CRC-32 in ARM nella IWRAM.
- Verifiche nuove: `test_battle_transition.py` (residente vero iniettato nel gioco emulato: la transizione di battaglia arriva alla battaglia; camminando il ciclo principale del gioco resta uguale al gioco senza residente, un tick per VBlank), `test_save_integrity.py` (salvataggio con e senza residente: flash identica tranne il tempo di gioco, pochi frame in meno perche il gioco occupato gira un po piu lento, e il suo checksum, valido), `measure_injected.py`, co-simulazione con il tempo libero (`--idle-start`).
- Risultati solo software (test-results/software-v0.13.0): co-simulazione fermo/corsa/verticale 60 frame su 60, 250/250, 299/299 e 298/299 immagini identiche; menu 497/497 identiche (0.12: 315/533); Centro Pokemon 741/769; battaglia 59,1 frame su 60, 672/690 identiche (0.12.0: 104/644). Gioco emulato con il residente: camminando 598/600 iterazioni come senza residente e 600 tick su 600 VBlank; in battaglia 900 tick su 900 e ritmo identico. Non provata su console; il firmware Pico 0.7.0 non cambia. Residente 6968 byte, loader 10656 byte.
- English: 0.13.0 fixes a block-hash weakness (swapped block halves hashed equal, leaving stale tiles in menus), streams queued graphics in the time Emerald spends spinning in WaitForVBlank (timer 1, packet type 13), never holds off the game's interrupts, and keeps the last complete image during scene changes. Save written with the resident is identical except for the play-time clock. Software-verified only.

## 0.12.3 - Il crash della battaglia: lettura delle code dentro il callback VBlank

- Causa del crash all inizio delle battaglie selvatiche, presente da 0.12.0 e riprodotta ora nell emulatore iniettando il residente vero nel gioco (`tools/test_battle_transition.py`): la transizione di battaglia genera un interrupt per riga; il residente eseguiva `observe()` prima del gestore IRQ del gioco e un ritardo di poche centinaia di cicli in quel punto (misurato: 1-5 cicli di attesa passano, 10 no) faceva perdere la sincronia degli interrupt di riga; il contatore VBlank del gioco si fermava (112 interrupt per frame invece di 228) e la console si bloccava. Ritardi dopo il gestore (fino a 25 righe) non danno problemi.
- Correzione: il wrapper IRQ non fa piu nulla prima del gestore (gli interrupt diversi dal VBlank saltano direttamente al gioco). Le code di copia (DMA3, animazioni tileset, sprite) sono lette da un piccolo thunk installato in `gMain.vblankCallback` solo nei tre callback noti (campo, Pokedex, squadra) e leggono al massimo 20 richieste per VBlank; se ce ne sono di piu si passa alla verifica della VRAM (`mark_all`). In ogni altra scena il callback del gioco non viene toccato.
- Corretto anche un ciclo infinito latente: una richiesta di copia con dimensione zero finiva in `words_equal`, che con 0 byte non termina.
- 0.12.2 (mai da usare): la regola "tick corto se IE contiene VCount" era sbagliata, IE vale 5 (VBlank e VCount) anche nel campo, e portava tutto lo stream a 0 fps. Ora la modalita corta (tick che finisce prima della riga 220, niente patch di layer, niente slot di risposta) vale solo fuori dai callback noti o con HBlank abilitato. Nelle battaglie misurate IE vale 5, poi 69 (VBlank, VCount, timer 3), mai HBlank.
- Il residente occupa 5968 byte; lo stack utile e circa 980 byte.
- Verifica: nel banco di prova con l emulatore due transizioni di battaglia diverse (0x81482c9 e 0x81472b5) arrivano al callback della battaglia con 899 VBlank su 900 frame; la 0.12.0 si ferma al frame 58. Fermo/cammino/corsa emulati invariati. Non ancora provata su console.

## 0.12.2 - Tick solo dentro il VBlank quando il gioco usa gli interrupt di riga

- Risultato hardware 0.12.1 (log-20260930-114237): tick limitati (massimo 99 righe, nessuno oltre 100) ma le battaglie facevano ancora crashare il gioco e restavano glitch in movimento. Causa probabile: nelle battaglie il gioco ascolta gli interrupt HBlank/VCount; il tick del residente girava in modalita IRQ fino a 50-60 righe nel frame successivo, quindi gli interrupt di riga restavano bloccati sulle prime righe visibili e l effetto per scanline si rompeva.
- Ora, fuori dai tre callback noti (campo, Pokedex, squadra) o quando IE contiene HBlank o VCount, il tick deve finire prima della riga 220: budget dalla riga di ingresso (`220 - entry_line`, il tick viene saltato se il gestore del gioco esce dopo la riga 208), niente patch di layer, niente firme da imparare, confronti ROM limitati a 256 parole, niente slot di risposta. Registri, palette e OAM continuano a viaggiare.
- Telemetria per il prossimo log: IE (7 bit) nei bit alti del campo blocchi in attesa, e un identificativo a 8 bit del callback VBlank nei bit alti del numero di record; il riepilogo dei log mostra i valori visti. Il residente riserva 0x100 byte in meno di stack (stack utile circa 980 byte, dimensione massima dei buffer invariata; RQ 8 richieste ROM per tick).
- Non ancora provata su console. I caricamenti di scena restano lenti e i tile arrivano con ritardo mentre si cammina (backlog di 10-18 blocchi con circa 45 righe per tick): limite di larghezza di banda del cavo software, non risolto.

## 0.12.1 - Tick limitati nelle scene sconosciute e pulsante dei log

- Correzione dal risultato hardware 0.12.0 (glitch neri e musica distorta all inizio di una battaglia in erba alta): 915 tick su 19371 duravano oltre 150 righe, fino a 217, con quasi nessun dato da inviare. Lo stadio dei registri scansionava tutta la VRAM senza limite e, dopo otto tick affamati, anche i blocchi perdevano il limite di tempo; il VBlank successivo del gioco partiva in ritardo. Ora la scansione dei blocchi caldi si ferma al blocco 9 e il raddoppio del tempo vale al massimo 2 volte il budget.
- Scene con callback sconosciuta (battaglia): audit a fette di 32 blocchi per tick invece di scansioni continue. Il polling della porta link da parte del gioco (Centro Pokemon) non forza piu la rilettura di tutta la VRAM. Confronti ROM limitati a 1024 parole per tick. Dopo un tick oltre 110 righe il residente salta 6 tick. Flag di telemetria: tick saltati prima del pacchetto e scena sconosciuta.
- Pagina web: pulsante "Scarica log" che crea un solo zip (riepilogo.json, rapporto, frames.jsonl, console, ultimi byte USB, ultimo frame). Lo stesso file viene salvato in dist/emerald-reports a ogni pressione e alla chiusura della sessione. Nuovo `tools/log_summary.py`.
- Verifica software: tick massimo emulato da 153 a 82 righe nel Centro Pokemon; test con callback sconosciuta e con registro link modificato a ogni frame falliscono sulla 0.12.0 (198 righe) e passano sulla 0.12.1. Fermo/cammino/corsa emulati invariati (60/60, 100/99/90%). Riepilogo hardware 0.12.0 in test-results/hardware-v0.12.0. Non ancora provata su console. I caricamenti di scena restano lenti (circa un blocco per VBlank): limite noto.
- English: 0.12.1 fixes ticks that ran whole frames on hardware (unbounded VRAM sweeps after a scene change or link-port polling), which delayed the game's own VBlank; adds a "Scarica log" button that produces one zip with all session logs. Software-verified only; scene loads remain slow.

## 0.12.0 - Un pacchetto per VBlank, copie dalla ROM e patch di layer

- Nuovo flusso 0x700: il residente invia un pacchetto per ogni VBlank con registri, palette e OAM aggiornati e con quanti blocchi VRAM entrano in un piccolo budget di righe; i blocchi rimasti restano in coda e il pacchetto dichiara quanti sono. Il PC (`stream_parser.py`) applica i record a una cache in esecuzione, tiene i frame in ordine finche restano blocchi in coda e li rilascia con il proprio stato; dopo un caricamento lungo mantiene l'ultima immagine completa. Protocollo in docs/PROTOCOLLO-STREAM.md. Pico 0.7.0 invariato: lo slot di risposta resta un END 0x600 ogni 30 VBlank.
- Tempo CPU come vincolo principale (misurato: il gestore del gioco esce attorno alla riga 205). Budget di righe dall'ingresso, con il costo di invio del pacchetto conteggiato; registri, palette e OAM mai trattenuti. Il residente non lavora se, al VBlank, il codice interrotto non e nel BIOS (il gioco e ancora occupato; al massimo tre volte di seguito) e lascia SELECT + R + A per cambiare la cadenza (ogni VBlank, uno su due, uno su tre). Coda delle animazioni dei tileset (0x02037624, contatore 0x03000F34) osservata insieme a coda DMA3 e richieste sprite.
- Copie dalla ROM: il GBA confronta VRAM e ROM parola per parola dopo il VBlank del gioco e invia un riferimento di cinque parole (tipo 10) al posto dei pixel; il PC lo ripete da un'immagine locale della cartuccia (`rom_cache.py`, `runtime/cache/`, esclusa dalla repository). Modo copia della cartuccia dal loader (tasto A al posto di START): 65536 pezzi da 256 byte con CRC32, validati dal PC prima del salvataggio.
- Patch di layer (tipo 12) al posto delle patch per blocco: una sola coppia di colonne o di righe per layer e passo di scorrimento (misurato: 64 parole per layer invece di circa 550 per lo schermo), a pezzi se non entra, con riferimento d'insieme sull'ultimo pezzo. Compressione LZ tolta dal residente: piu lenta dell'invio grezzo.
- Correzioni trovate con il co-simulatore: firma a 32 bit degenere sui blocchi OAM tutti uguali (hash a zero); firme di layer a 16 bit con somma e rotazione che collidevano su voci di mappa consecutive (ora moltiplicazione); le firme dell'altra dimensione vengono ignorate finche un invio a pezzi non finisce.
- Strumenti: `cosim_stream.py` (gioco in mGBA, vero codice ARM in Unicorn con modello dei cicli, ricevitore del PC, confronto dei pixel), `measure_stream.py`, `measure_gameplay.py --run`, build con toolchain locale (`GBM_ARM_TOOLCHAIN`). Test: `test_stream_parser.py` (17), `test_rom_dump.py` (2), `test_stream_resident.py` (controlli 4 + scene).
- Risultati solo software (test-results/software-v0.12.0): con il gioco emulato fermo, camminando, in verticale e correndo lo stream pubblica 60 frame ogni 60 del gioco, 96-100% dei frame identici al frame emulato; ciclo principale del gioco emulato 1197/1198 camminando e 1197/1198 correndo. Menu e cambi scena restano lenti (secondi). Nessuna prova fisica: tempi del Link, audio e browser da verificare su console. 0.11.0 resta disponibile con B.
- English: stream 0.12.0 sends one packet per game frame, replays ROM-sourced copies from a local cartridge image made by a one-time GBA dump mode, patches scrolling maps as one column or row pair per layer, and yields to a busy game. Software-only verification; no physical test yet.

## 0.11.1 - Publication sources and notices / Sorgenti e avvisi per la pubblicazione

- English-first README, Italian counterpart, setup guide, architecture and contribution guidance. Credits: hacke & Lain for concept/direction; GBMirroring development entirely with GPT 6 Astra, preserving upstream authorship.
- GPL-3.0 project license and dependency notices. Supplied legacy Celio UF2 matched byte-for-byte; pinned upstream archive and full supplier patch included with offline reconstruction. All 11 file patches verified. Individual authorship of three pre-existing changes remains unidentified; supplier GPL declaration retained. No claim of a verified identical binary rebuild.
- Current 27-word Celio PIO reference verified; old test now uses the included reference instead of a private development path. No vendor transport code or streaming binary changed. Runtime/firmware integrity checks pass; no hardware test or new FPS claim.
- README inglese/italiano, guida, architettura e contributi. Crediti hacke & Lain e sviluppo GBMirroring interamente con GPT 6 Astra, senza attribuirsi codice upstream.
- Licenza GPL-3.0 e avvisi delle dipendenze. UF2 storico identico a quello ricevuto; base e patch completa incluse, ricostruzione offline verificata su 11 file. Autori individuali di tre modifiche preesistenti non identificati; conservata dichiarazione GPL ricevuta. Nessuna ricompilazione identica certificata.
- Riferimento PIO verificato e percorso privato rimosso dal test. Moduli vendor e binari streaming invariati. Controlli d'integrità superati; nessuna nuova prova hardware o prestazione dichiarata.

## 0.11.0 - Patch delle mappe e scenario Ceneride

- Codec batch 9 per gruppi di quattro colonne nelle mappe. Firme compatte calcolate in ARM e controllo delle due firme integrali sul PC; ripiego sui codec completi se nessun gruppo risulta cambiato. Corrette collisioni strutturate trovate con scene reali.
- Dizionario 64 voci, shadow registri compatto, nessun nuovo lavoro LZ su patch gia selezionate. Mantiene 155 parole per intervento, range RAM e firmware Pico unificato 0.7.0. Loader 5824 byte, residente 4160 byte.
- Fixture Ceneride da copia in memoria del salvataggio locale. Confronto emulato orizzontale 13,64 -> 21,35 FPS; verticale 21,25 -> 21,95; Centro 18,96 -> 20,76. Porto Selcepoli 33,20 -> 31,46: beneficio non uniforme. Main 1198/1200 con e senza cattura.
- Replay di 120 scene congelate: codice ARM reale, GPIO simulato, cache PC identica byte per byte. Verificati codec, fallback RAW, limiti, recupero, boot e firma cartuccia, multiboot simulato e pacchetto portatile. Nessuna certificazione hardware o 30 FPS ovunque; squadra e transizioni restano sotto il target.
- Contatori automatici per regione grafica e codec nei rapporti, senza un secondo test manuale. Utente disponibile ad aggiornare il Pico tra release, mantenendo un firmware unico durante la procedura.

## Collaudo hardware 0.10.0 - target esterno ancora aperto

- Sessione 181547: 4052 frame, 20,16 FPS medi, nessun errore Link o scarto renderer. Stutter esterno in movimento ancora forte secondo l utente; Centro Pokemon fluido anche camminando.
- Aggiornamenti grandi: 17+ blocchi richiedono in mediana 2936 byte e 16 interventi. Rendering PC picco 1,38 ms. Il log non identifica gli indirizzi dei blocchi: la riscrittura dei tilemap durante lo scorrimento rimane un ipotesi da verificare.
- Registrata evidenza ripulita; nessun nuovo binario. Le misure emulatore precedenti non certificano questa scena hardware.

## 0.10.0 - Compressione in RAM veloce e cache ampliata

- Compressione RLE/LZ e patch registri/OAM in IWRAM; sender raggruppato a quattro bit per liberare spazio senza cambiare ordine o polarita. Tolta una copia RAW ridondante. Dizionario 32 -> 128 voci con confronto dei due hash, parser esteso e test del limite 127.
- Scansione selettiva anche per i callback italiani del Pokedex e della squadra, verificati sul codice locale; controllo completo al cambio di callback e fallback conservativo per callback sconosciuti.
- Cammino ripetibile emulato: 667 catture/1200 frame, 33,20 FPS contro 197/1200, 9,81 FPS della 0.9.0. Finestra minima di un secondo: 13 catture; nessuna garanzia di 30 costanti. Ciclo Main: 1197/1200 contro 1198/1200 senza residente. Non sono misure hardware/audio.
- Loader pronto da 5424 byte, residente 3768 byte, Pico 0.7.0 invariato. Avvio unico 14-AVVIA-SMERALDO.bat; B conserva la baseline 0.8.0. Protocollo ARM, compressione, fallback RAW incomprimibile, CRC, boot mGBA e multiboot simulato verificati.
- Persistono tempi di caricamento e cali in alcune scene: squadra stabile circa 23 FPS emulati. Cache iniziale da ROM e trasporto a risorse indipendenti non integrati. Obiettivo 30 sostenuti in ogni situazione ancora aperto.
- Ripristinati ROM e salvataggio locali per i test: entrambi letti senza modificarli, esclusi dalla repository e dal pacchetto.

## Risultato hardware 0.9.0 e prototipo di patch VRAM

- 2327 frame consecutivi, 10,6295 FPS medi, zero CRC/header/gap/render drop. Renderer picco 1,65 ms, coda USB picco 0,49 ms. Utente: circa 30 da fermo, circa 4 camminando; gioco e audio GBA ancora fluidi.
- Transazioni senza modifiche: mediana 78 byte e 1 intervento; con 5-16 blocchi modificati: 1518 byte e 10 interventi; oltre 16 blocchi: 3608 byte e 21 interventi. Il browser non e il collo di bottiglia osservato.
- Prototipo isolato di patch VRAM da 16 byte, con CRC32 del blocco ricostruito per respingere collisioni del filtro CRC16 o riferimenti sbagliati. Cache limitata, ombra registri compattata e dizionario ridotto per rientrare in RAM. Test ARM: modifica di 16 byte ricostruita esattamente in una transazione da 128 byte.
- Replay parziale della coda: confronto ideale 36686 -> 25952 byte su 272 aggiornamenti VRAM noti (-29,3%). Non e un dato sull intera sessione; non basta a dimostrare il passaggio da 4 a 30 FPS.
- Nessuna nuova release. Il prototipo compila solo in build/emerald-sparse; il launcher resta 0.9.0. ROM e salvataggio locali risultano eliminati: per prove reali in emulazione recuperare almeno il file GBA, il salvataggio e opzionale. Il trasporto a risorse separate rimane da completare.

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


## 0.3.2 — Diagnostica della ricezione

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
