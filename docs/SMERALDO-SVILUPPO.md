# Smeraldo italiano: residente sperimentale 0.5.0

Il loader controlla BPEI, firme delle routine e CRC32 0x6ee38ad1 dei primi 8192 byte della cartuccia. Il profilo e specifico della revisione verificata localmente; non supporta ancora Verde Foglia o altre lingue. Il vecchio profilo candidato resta documentazione preliminare.

Il residente occupa EWRAM da 0203cf80, con stack privato 0203f800..0203fc00 e stadio bootstrap a 0203fe00. Il wrapper richiama l IRQ originale a 03002750, quindi il lavoro di cattura. Le routine veloci vengono copiate nella coda inutilizzata del buffer del dispatcher IRQ, da 03002950 entro 03002f50. I linker impongono i limiti. Bootstrap e riserva seguono il comportamento analizzato del materiale ricevuto; la compatibilita durante tutta la partita richiede ancora collaudo.

SELECT+L+R abilita/pausa; una cattura ogni sei VBlank del gioco. 393 blocchi da 256 byte descrivono registri shadow, palette, OAM e VRAM. Due hash rolling a 32 bit identificano i blocchi cambiati (collisioni teoricamente possibili); keyframe ogni 120 catture e alla riattivazione. Pacchetti BEGIN/BLOCK/END con CRC32 payload, CRC16 header, sequenza e conteggio blocchi: il PC applica solo transazioni complete e attende un keyframe dopo perdita. Il sender mantiene SC basso tra invii per evitare fronti spuri. Le pause di invio consumano tempo del gioco.

Il PC usa il core mGBA incluso con un nostro homebrew inattivo e inietta lo stato grafico: non carica o esegue Pokemon. Non ricostruisce modifiche per scanline; il flag DMA0 e solo un avviso, non un rilevatore completo di tutti gli effetti. UVC autonomo ancora da realizzare.

Verifica: python tools/build_emerald.py; python tools/test_emerald.py; python tools/test_sd_video.py. Il test tools/test_emerald_mgba.py accetta --rom e --save locali, legge senza modificare gli originali, e simula bootstrap, movimento/menu e timing. Non prova il multiboot elettrico, USB reale, tutte le battaglie o il salvataggio con residente. Il normale utente non necessita di ROM, salvataggi o toolchain sul PC.

Risultato software selezionato: test-results/software-v0.5.0/summary.json. Prova fisica: ../PROVA-SMERALDO.md. Il banco homebrew 0.4.2 e distinto e non dimostra le prestazioni del gioco.
