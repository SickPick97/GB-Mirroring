# Smeraldo italiano: residente sperimentale 0.5.0

Il loader controlla BPEI, firme delle routine e CRC32 0x6ee38ad1 dei primi 8192 byte della cartuccia. Il profilo e specifico della revisione verificata localmente; non supporta ancora Verde Foglia o altre lingue. Il vecchio profilo candidato resta documentazione preliminare.

Il residente occupa EWRAM da 0203cf80, con stack privato 0203f800..0203fc00 e stadio bootstrap a 0203fe00. Il wrapper richiama l IRQ originale a 03002750, quindi il lavoro di cattura. Le routine veloci vengono copiate nella coda inutilizzata del buffer del dispatcher IRQ, da 03002950 entro 03002f50. I linker impongono i limiti. Bootstrap e riserva seguono il comportamento analizzato del materiale ricevuto; la compatibilita durante tutta la partita richiede ancora collaudo.

SELECT+L+R abilita/pausa; una cattura ogni sei VBlank del gioco. 393 blocchi da 256 byte descrivono registri shadow, palette, OAM e VRAM. Due hash rolling a 32 bit identificano i blocchi cambiati (collisioni teoricamente possibili); keyframe ogni 120 catture e alla riattivazione. Pacchetti BEGIN/BLOCK/END con CRC32 payload, CRC16 header, sequenza e conteggio blocchi: il PC applica solo transazioni complete e attende un keyframe dopo perdita. Il sender mantiene SC basso tra invii per evitare fronti spuri. Le pause di invio consumano tempo del gioco.

Il PC usa il core mGBA incluso con un nostro homebrew inattivo e inietta lo stato grafico: non carica o esegue Pokemon. Non ricostruisce modifiche per scanline; il flag DMA0 e solo un avviso, non un rilevatore completo di tutti gli effetti. UVC autonomo ancora da realizzare.

Verifica: python tools/build_emerald.py; python tools/test_emerald.py; python tools/test_sd_video.py. Il test tools/test_emerald_mgba.py accetta --rom e --save locali, legge senza modificare gli originali, e simula bootstrap, movimento/menu e timing. Non prova il multiboot elettrico, USB reale, tutte le battaglie o il salvataggio con residente. Il normale utente non necessita di ROM, salvataggi o toolchain sul PC.

Risultato software selezionato: test-results/software-v0.5.0/summary.json. Prova fisica: ../PROVA-SMERALDO.md. Il banco homebrew 0.4.2 e distinto e non dimostra le prestazioni del gioco.


## Aggiornamento 0.5.1
Scheduler spostato in EWRAM per rispettare lo stesso spazio IWRAM verificato. Sender, hash e CRC restano nella coda IRQ. Una transazione viene distribuita fra IRQ: fino a 64 confronti e un invio di 256 byte per intervento; fuori VBlank o dalla linea 224 rinvia. Il limite non garantisce che la routine termini entro VBlank. L intera immagine non e piu uno snapshot atomico: possibili artefatti transitori, da misurare sul gioco reale. RCNT considera i bit in ingresso separatamente dalle uscite; reinizializzazione rilevata forza keyframe.

Header 0x501 compatibile nella struttura con 0x500. Il PC cerca magic e header CRC a qualsiasi bit nelle parole PIO; un fronte extra non rende definitivamente illeggibile il flusso. Rimangono CRC payload, conteggi e sequenze; una transazione incompleta richiede comunque keyframe. La coda raw finale di 64 KiB rimane solo nei rapporti locali. I 90 confronti esatti del renderer riguardano snapshot coerenti forniti dal test, non certificano la fedelta temporale della cattura distribuita.


## 0.6.0
Protocollo 0x600: literal type 1 (slot nei bit alti di block), reference type 3 (slot nel payload), RLE type 4, patch halfword type 5. Cache 64 slot a rimpiazzo deterministico, confronto con due hash a 32 bit come nel rilevatore di modifiche; collisioni teoriche restano possibili. Keyframe azzera il dizionario su entrambe le estremita. Il decoder invalida il riferimento se una transazione e incompleta. RLE non espande oltre 256 byte; patch hot con bitmap di 128 halfword. Cinque buffer precedenti per registri e OAM, nessuna copia completa della VRAM sul GBA.
Scanner scan_next salta i blocchi invariati interamente in IWRAM; scheduler e compressione rimangono ARM in EWRAM. La variante Thumb non e stata mantenuta perche il test mGBA falliva. Limiti del linker invariati; __end__=0203f620, inferiore allo stack a 0203f800. L END include contatore finale del gioco, interventi, parole e picco scanline misurato prima dell END stesso; non e una misura completa di cicli CPU.
Unificazione: PIO1 master multiplayer mutuamente esclusivo con PIO0 ricevitore. STOP/disconnessione rilasciano i pin. Una sola interfaccia CDC e sequenza BOOT/T/W/START/STOP; nessuna compatibilita completa Celio online implicita. Il protocollo multiboot Python resta invariato; il nuovo trasporto accoda parole e cambia timing alla consegna al PIO. Test simulato non certifica timing elettrico.
Non sono ancora implementati hook sulle code di aggiornamento del gioco o coerenza atomica tra tutte le risorse di un frame. FPS sotto target anche in emulazione: non dichiarare completato il piano 10 FPS.
