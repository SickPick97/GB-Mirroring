# GBMirroring

Pacchetto **0.11.1**: documentazione di pubblicazione, licenze e provenienza dei sorgenti aggiornate. Binari streaming invariati: residente **0.11.0**, Pico **0.7.0**. Codice proprio [GPL-3.0](LICENSE); dipendenze e sorgenti in [THIRD_PARTY.md](THIRD_PARTY.md).

**Streaming di Pokémon Smeraldo da un GBA SP senza modifiche interne al browser del PC, attraverso Raspberry Pi Pico e porta Link.**

[English](README.md) · **Italiano** · [Avvio](PROVA-SMERALDO.md) · [Architettura](docs/ARCHITECTURE.md#italiano)

GBMirroring è un progetto sperimentale hardware/software che mostra sul PC la partita eseguita da una cartuccia reale. Il gioco gira sulla console; un piccolo programma residente esporta lo stato grafico attraverso il cavo Link, e il PC ricostruisce l'immagine per il browser locale e OBS.

**Idea e direzione del progetto: hacke e Lain. Lo sviluppo di GBMirroring è stato effettuato interamente con AI, usando GPT 6 Astra.** Assemblaggio hardware, prove, feedback e decisioni sono contributi umani. Codice e progetti preesistenti restano attribuiti ai rispettivi autori: la dichiarazione sullo sviluppo AI non si riferisce alla loro paternità.

Questa prima pubblicazione condivide codice funzionante, strumenti pronti e limiti misurati. **Non garantisce ancora uno stream stabile a 30 FPS in ogni scena.**

## Cosa funziona

- Streaming da cartuccia reale provato su **GBA SP e Pokémon Smeraldo italiano originale, BPEI revisione 0**.
- Adattatore **Raspberry Pi Pico RP2040** con un solo firmware per multiboot e streaming, senza cambiarlo durante la procedura.
- Applicazione portatile Windows x64 e visualizzatore web locale utilizzabile anche in OBS.
- Cache grafica, aggiornamenti differenziali, compressione, verifiche di integrità e recupero automatico.
- Gioco e audio sulla console rimasti fluidi nelle recenti prove hardware dell'utente. Questo non significa che il browser raggiunga lo stesso framerate.

La documentazione pubblica dà priorità all'inglese e affianca l'italiano. Alcune note storiche e i messaggi dei programmi esistenti sono ancora solo in italiano; la guida inglese spiega le richieste del launcher corrente.

## Configurazione supportata

| Componente | Configurazione attuale |
|---|---|
| Console | GBA SP; la compatibilità con altri GBA non è certificata |
| Cartuccia | Pokémon Smeraldo italiano originale, BPEI rev. 0 |
| Adattatore | Pico RP2040 sulla [scheda di agtbaskara](https://github.com/agtbaskara/game-boy-pico-link-board) |
| Cavo | Cavo GBA con nodo centrale provato; spinotto piccolo all'adattatore, grande al GBA; selettore GBA |
| PC | Windows 10/11 x64, collegamento USB dati e browser |
| Software | Residente Smeraldo 0.11.0, firmware Pico unificato 0.7.0 |

Non servono modifiche interne alla console. Il profilo attuale usa indirizzi specifici e controlla la revisione della cartuccia. Altre lingue di Smeraldo, Rosso Fuoco/Verde Foglia, giochi GB/GBC e cartucce arbitrarie **non sono supportati da questa release**. Un adattatore o cavo diverso può avere collegamenti differenti.

## Avvio rapido

1. Scarica lo ZIP completo da **Code → Download ZIP** ed estrailo in una cartella scrivibile. Non avviare i BAT dentro lo ZIP.
2. Se il Pico non usa già il nostro firmware unificato 0.7.0, tieni premuto BOOTSEL mentre colleghi USB e copia `dist/gbmirroring-unified-v0.7.0.uf2` nella sua unità. Per questa release basta una volta.
3. Accendi il GBA senza cartuccia. Avvia **14-AVVIA-SMERALDO.bat** e premi **INVIO** per il multiboot.
4. Quando richiesto sulla console, inserisci Smeraldo italiano, premi **START** ed entra nella partita.
5. Quando il PC indica **PRONTO**, premi **SELECT + L + R** sul GBA. Si apre **http://127.0.0.1:8765**. Lascia aperto il BAT.

Il pacchetto comprende Python portatile, librerie USB, renderer, homebrew e UF2 compilati. Non devi compilare, fornire una ROM commerciale al PC o avere la cartella privata di sviluppo.

Per OBS: sorgente Browser **http://127.0.0.1:8765/?clean=1**, 240 × 160 o multipli interi. Il browser mantiene circa 200 ms di buffer. Il visualizzatore attuale non trasmette l'audio del gioco.

[Guida completa, recupero e collaudo →](PROVA-SMERALDO.md)

## Come funziona

Il PC carica via multiboot un piccolo programma in RAM. Il loader verifica la cartuccia e avvia il gioco mantenendo il residente. Questo osserva registri grafici, palette, OAM e VRAM, comprime le modifiche e le invia attraverso i segnali GPIO della porta Link. Il Pico riceve le parole con PIO/DMA e le inoltra via USB CDC. Il PC verifica le transazioni, aggiorna una cache grafica e usa il renderer basato su mGBA per produrre l'immagine mostrata nel browser.

La porta Link non espone un segnale video LCD grezzo. Il PC ricostruisce le risorse esportate dalla console; non esegue una seconda copia del gioco da una ROM commerciale. La 0.11.0 aggiunge piccole patch per gruppi di colonne delle mappe durante lo scorrimento, controllando il blocco ricostruito prima di accettarlo.

## Prestazioni documentate

| Evidenza | Risultato | Interpretazione |
|---|---|---|
| Sessione fisica 0.10.0 | 20,16 frame ricevuti/s medi, con forti scatti camminando all'aperto | La media nasconde intervalli molto peggiori |
| Cammino orizzontale emulato a Ceneride, 0.11.0 | 13,64 → 21,35 catture/s rispetto alla 0.10.0 | Stesso scenario controllato, non misura degli FPS nel browser fisico |
| Callback Main del gioco emulato, 0.11.0 | 1198 aggiornamenti su 1200 frame, con e senza cattura | Avanzamento del gioco controllato separatamente |
| Replay ARM 0.11.0 | 120 scene congelate su 120 ricostruite esattamente | Correttezza del codec, non prova di coerenza temporale dal vivo |

Alla preparazione della pubblicazione non è ancora registrato un test fisico della 0.11.0. Menu, lotte, cambi scena e aree esterne complesse possono abbassare gli FPS dello stream. Gli effetti per scanline sono incompleti. Frame interpolati e refresh ripetuti del browser non sono contati come nuovi frame ricevuti.

[Registro hardware](docs/VALIDAZIONE-HARDWARE.md) · [Risultati software](test-results/software-v0.11.0/summary.json) · [Limiti e sviluppo futuro](docs/ARCHITECTURE.md#italiano)

## Origine e crediti

Il lavoro nasce dagli esperimenti di hacke e Lain con adattatori Link, collegamenti online e un progetto separato per giocare insieme a Smeraldo. L'unione delle repository è prevista in futuro. **Il software cooperativo non è attualmente incluso né presentato come una funzione di GBMirroring.**

Ringraziamenti a [agtbaskara](https://github.com/agtbaskara/game-boy-pico-link-board) per la scheda, [Celio-Link](https://github.com/Celio-Link) per il trasporto e la sequenza PIO da cui deriva il multiboot, agli autori dei moduli `mb_multi.py` e `usb_link.py` forniti al progetto, a [pret/pokeemerald](https://github.com/pret/pokeemerald) per le strutture del gioco, a [mGBA](https://github.com/mgba-emu/mgba) per il renderer e a Pico SDK, TinyUSB, Python, PyUSB e libusb.

[THIRD_PARTY.md](THIRD_PARTY.md) documenta attribuzioni e distribuzione. Nessuna ROM commerciale o salvataggio è incluso. Pokémon e Nintendo identificano la compatibilità; il progetto è indipendente, non affiliato né approvato dai titolari. La pubblicazione documenta il lavoro e la sua cronologia, senza rivendicare esclusività o priorità su altri progetti.

## Orientarsi e contribuire

`firmware/emerald-columns` contiene il residente corrente; `firmware/unified` il firmware Pico; `tools` launcher, protocolli e test; `native/renderer` l'adattatore del renderer e i sorgenti mGBA corrispondenti; `runtime` le dipendenze portatili; `dist` i binari versionati; `test-results` le evidenze selezionate; `docs` le guide.

Per una segnalazione indica versione, adattatore/cavo, lingua e revisione della cartuccia, scena e comportamento sul GBA. Controlla i rapporti prima di caricarli: i log grezzi possono contenere percorsi locali o identificativi dei dispositivi. Non allegare ROM o salvataggi. Vedi [CONTRIBUTING.md](CONTRIBUTING.md#italiano).
