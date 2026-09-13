# Patch mappe 0.11.0

Versione esterna invariata 0x600, contenitore batch tipo 7. Il residente emette il tipo interno 9 solo nel batch; il Pico 0.7.0 continua a ricevere parole e riconoscere END, senza interpretare il codec interno. Nessun cambiamento elettrico.

Tipo 9: tag identico agli altri blocchi (slot dizionario nei bit alti, indice nei nove bassi). Ammessi gli indici 233..256, corrispondenti ai tre screen block VRAM 28..30. Ogni risorsa contiene quattro righe da 64 byte.

Payload little endian:

- uint16: maschera degli otto gruppi di quattro colonne; bit alti obbligatoriamente zero;
- due uint32: firme dell'intero blocco, identiche a hash_begin;
- per ogni gruppo attivo, in ordine crescente, otto byte per riga, quattro righe in ordine. Offset nella risorsa: riga * 64 + gruppo * 8.

Lunghezza esatta: 10 + 32 * popcount(mask). Vietato su keyframe. Dopo applicazione a una copia del riferimento, il ricevitore verifica entrambe le firme integrali, quindi aggiorna cache e dizionario. Il CRC esterno continua a proteggere il payload. Su errore invalida la transazione e usa il recupero gia presente.

Le firme compatte uint16 del residente sono solo un filtro per scegliere gruppi; moltiplicazione e mescolamento evitano le collisioni strutturate emerse nel replay di Ceneride. Non costituiscono una prova di uguaglianza. Se tutte coincidono nonostante il blocco sia cambiato, si usa un codec completo. Le firme vengono aggiornate soltanto dopo l'inserimento della risorsa nel batch, mai quando manca spazio e il lavoro viene rinviato.

I test verificano geometria, limiti, riferimento errato con CRC valido, codec ARM reale e replay di scene locali. Nessuna firma finita esclude matematicamente tutte le collisioni; il controllo integrale riusa le due firme preesistenti del protocollo.

## Scenario ripetibile

prepare_sootopolis_state.py usa esclusivamente ROM e salvataggio locali, cambiando una copia in memoria per posizionare il giocatore davanti al Centro. Nessuna modifica ai file originali. Le strutture e la riscrittura delle strisce di mappa sono documentate nei sorgenti primari [field_camera.c](https://github.com/pret/pokeemerald/blob/master/src/field_camera.c), [fieldmap.c](https://github.com/pret/pokeemerald/blob/master/src/fieldmap.c) e [mappa di Ceneride](https://github.com/pret/pokeemerald/blob/master/data/maps/SootopolisCity/map.json).

La fixture riproduce la geometria, non esattamente eventi, NPC e stato della partita dell'utente. measure_motion.py misura catture in mGBA; measure_gameplay.py misura separatamente il callback Main. check_columns_replay.py invia scene congelate attraverso istruzioni ARM in Unicorn e confronta tutti i byte ricevuti. Queste tre verifiche hanno scopi diversi e nessuna sostituisce gli FPS presentati dal browser sull'hardware reale.
