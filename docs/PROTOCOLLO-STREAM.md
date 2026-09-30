# Flusso 0.12/0.13: un pacchetto per VBlank piu il tempo libero

Versione esterna 0x700. Il Pico unificato 0.7.0 non cambia: continua a trasportare parole e a riconoscere il solo END 0x600 usato per lo slot di risposta. Nessun cambiamento elettrico.

## Perche

Le misure sul residente 0.11.0 mostrano che il costo non e la banda del cavo ma il tempo CPU disponibile a ogni VBlank: il gestore del gioco termina attorno alla riga 205, e ogni transazione globale ferma il flusso finche tutti i blocchi non sono stati inviati. Nel flusso 0.12 il GBA invia sempre un pacchetto per VBlank con lo stato piccolo (registri, palette, OAM) e con quanti blocchi VRAM ha potuto elaborare nel tempo disponibile. I blocchi rimasti restano "sporchi" e vengono inviati nei VBlank successivi.

## Pacchetto

Intestazione da 12 parole come negli altri formati: firma `b47e 5647`, versione `0x700`, tipo, sequenza a 32 bit, numero di parole del payload (massimo 240), campo ausiliario, CRC32 del payload, CRC16 dell intestazione, marcatore `5aa5`. Il residente limita il payload a 224 parole.

Tipi: 10 = tick, 11 = pezzo di ROM (solo modo copia), 12 = fine copia. Il pacchetto 0x600 tipo 2 continua a essere emesso ogni 30 tick soltanto per aprire lo slot di risposta; il PC lo usa per sapere se il Pico risponde.

### Tick (tipo 10)

Sei parole di campi, poi i record:

| Parola | Significato |
|---|---|
| 0 | bit0 keyframe, bit1 DMA raster attivo, bit8 risposta del Pico disponibile, 0x2000 marca del flusso |
| 1-2 | contatore VBlank del gioco (orologio per la presentazione nel browser) |
| 3 | blocchi VRAM noti come modificati e ancora da inviare dopo questo tick |
| 4 | numero di record |
| 5 | bassi 8 bit: righe di lavoro del tick precedente; alti 8 bit: parole del tick precedente |

Record: `tag` (slot dizionario nei bit alti, indice blocco nei nove bassi), descrittore (tipo nei bit alti, parole del corpo nei bassi), corpo. Tipi di blocco come in 0.11: 1 grezzo, 3 dizionario, 4 RLE, 5 patch registri/OAM, 6 LZ. Il tipo 9 (colonne per blocco) e sostituito dal tipo 12, patch di un intero layer. Nuovo tipo 10: copia dalla ROM.

### Copia dalla ROM (record tipo 10)

Corpo di cinque parole: sorgente (32 bit), destinazione VRAM (32 bit), dimensione in byte. Il PC ripete la copia dalla propria immagine della cartuccia. Il GBA emette il record soltanto dopo aver confrontato, parola per parola, la VRAM di destinazione con la ROM: la replica e quindi esatta per i byte coperti. Le richieste vengono lette prima dell IRQ del gioco (coda DMA3, coda animazioni tileset, richieste sprite) e confermate dopo, quando la copia e stata eseguita. I blocchi coperti per intero aggiornano subito la firma locale; i blocchi coperti in parte non aggiornano la firma e vengono riverificati dall audit a rotazione. Se la conferma fallisce, il blocco segue la strada normale.

### Patch di layer (record tipo 12)

Le tre mappe di sfondo (screen block 28..30, blocchi 233..256, otto blocchi da 256 byte ciascuna) cambiano quando il gioco scorre: una nuova colonna di metatile, o due righe. Il tag contiene il primo blocco del layer (233, 241 o 249). Corpo: flag (bit0 = parziale), maschera di 16 coppie di colonne, maschera di 16 coppie di righe, riferimento a 32 bit (XOR delle firme a 64 bit degli otto blocchi, ripiegate a 32), poi i dati: per ogni coppia di colonne attiva le due voci di ogni riga (32 righe x 4 byte), per ogni coppia di righe attiva due righe intere (128 byte). Lunghezza esatta 5 + 64 x gruppi parole.

Il residente usa la patch soltanto se conosce la copia del PC: per ogni layer ricorda 16 firme di coppie di colonne e 16 di coppie di righe (16 bit, miscela con moltiplicazione) del contenuto che il PC possiede. Una cella cambiata sta sia in una coppia di colonne sia in una coppia di righe che risultano cambiate: basta inviare l'insieme piu piccolo (per un passo orizzontale una coppia di colonne per layer, per un passo verticale una coppia di righe). Se non entra in un pacchetto viene inviata a pezzi: i pezzi parziali (flag 1) non hanno riferimento, aggiornano soltanto le firme dei gruppi inviati e fissano la dimensione (colonne o righe) fino alla fine; il pezzo finale porta il riferimento e riallinea tutte le firme. I layer non ancora noti (dopo un keyframe o una perdita) viaggiano blocco per blocco; le firme si imparano quando i loro otto blocchi risultano tutti puliti.

Il PC ricostruisce i 2 KB, calcola la firma di ciascun blocco e confronta il riferimento sul pezzo finale: se non coincide invalida la cache e chiede un keyframe. Il residente non usa la compressione LZ (il tipo 6 resta decodificabile): un blocco nuovo che RLE e patch non riducono viaggia grezzo, che costa meno tempo CPU che comprimerlo.

## Ricezione

Il PC applica ogni record alla cache in esecuzione, nell ordine di arrivo. Un salto di sequenza invalida la cache e richiede un keyframe. Ogni tick produce uno stato di presentazione (registri, palette e OAM del tick, VRAM corrente). Se `blocchi in attesa` e maggiore di zero, i frame restano in coda ordinata (massimo 8) e vengono rilasciati insieme quando la cache e completa, ciascuno con il proprio stato e il proprio orologio. Dopo un keyframe non si pubblica nulla finche la cache non e completa. Oltre il limite di attesa si rilascia comunque, segnalando il frame come incompleto. La coda di presentazione del browser (circa 200 ms) assorbe le raffiche.

Limite noto: un frame rilasciato dopo un ritardo usa la VRAM piu recente, non quella del suo istante. E una differenza di pochi tick sui blocchi che erano ancora in coda, non un frame inventato.

## Copia della cartuccia

Al menu del GBA, A invece di START avvia una lettura sequenziale della ROM (65536 pezzi da 256 byte, ognuno con CRC32). Il PC ricostruisce l immagine, la valida (dimensione, codice BPEI, guardie del profilo, CRC dell intestazione) e la salva in `runtime/cache/emerald-bpei.rom`, cartella esclusa dal controllo di versione. Si fa una volta sola per cartuccia. Nessun dato della ROM viene distribuito.

## Verifiche software

`test_stream_parser.py` (ordine, attesa, rilascio forzato, salti di sequenza, copia ROM, fault), `test_rom_dump.py` (loader ARM in emulazione contro l immagine locale) e `cosim_stream.py` (gioco in mGBA, residente ARM in Unicorn con modello dei cicli, decodifica del PC). La co-simulazione stima tempi CPU e completezza del flusso; non misura tempi elettrici, audio o frame del browser.


## Telemetria aggiunta in 0.12.1-0.12.3

Nella parola di flag: bit 4-6 tick saltati prima di questo pacchetto (0-7), bit 11 modalita corta (scena sconosciuta o HBlank abilitato). La parola 3 porta nei nove bit bassi i blocchi in attesa e nei sette alti IE (VBlank, HBlank, VCount, timer 0-3); la parola 4 porta nei bit bassi il numero di record e nei bit alti un identificativo a 8 bit del callback VBlank del gioco (xor dei tre byte bassi dell indirizzo). Il ricevitore li espone come `skipped_ticks`, `unknown_scene`, `interrupt_enable`, `callback_id` e il pulsante dei log li riassume.

## 0.13: tempo libero del gioco e interrupt mai bloccati

Smeraldo non ferma la CPU in attesa del VBlank: gira in un ciclo (`WaitForVBlank`, 0x080008c6-0x080008ce) finche `gMain.intrCheck` non segnala il VBlank. Quel tempo, di solito decine di righe per frame, era inutilizzato.

- Il residente programma il timer 1 (fermo durante il gioco; nella tabella interrupt del gioco il suo posto e una funzione vuota) per un controllo ogni dieci righe. Se l interrupt ha fermato il gioco dentro quel ciclo con il flag VBlank ancora spento, il frame del gioco e finito: il residente legge le code di copia per il prossimo VBlank e invia i blocchi in attesa, poi verifica il resto della VRAM, fino alla riga 150. Ogni blocco parte solo se c e il tempo per finirlo (circa sei parole per riga, misurato in mGBA); se il VBlank arriva comunque, il tick viene eseguito subito dopo.
- Pacchetto tipo 13 (stessa intestazione e stessi sei campi del tipo 10): blocchi inviati nel tempo libero. Non genera un immagine: completa la cache del tick precedente e aggiorna i blocchi in attesa. Parola 5: parole inviate nel tempo libero in questo frame.
- Tick e lavoro nel tempo libero girano in modalita di sistema con gli interrupt abilitati: HBlank, VCount (sincronizzazione audio alla riga 150), timer e seriale del gioco vengono serviti subito. Prima del gestore del gioco il residente esegue solo un confronto. Il controllo "gioco occupato" usa l indirizzo interrotto salvato dal BIOS confrontato con il ciclo di attesa (prima leggeva un indirizzo del BIOS e non scattava mai).
- Le copie osservate prima del VBlank vengono applicate alle maschere solo dopo il VBlank, quando il gioco le ha eseguite: il residente non invia un blocco prima che cambi.
- Dopo un cambio di scena tutti i blocchi non verificati contano come in attesa: il PC tiene l ultima immagine completa invece di mostrare tile vecchi e nuovi mescolati. Il PC trattiene fino a 30 tick (240 con piu di 40 blocchi in attesa) e al rilascio mostra al massimo gli ultimi 12.
- CRC-32 calcolato in ARM nella IWRAM (quattro bit per passo).
