# GBMirroring

Pacchetto **0.12.1**: residente **0.12.1** e firmware Pico **0.7.0** invariato. Codice proprio [GPL-3.0](LICENSE); dipendenze e sorgenti in [THIRD_PARTY.md](THIRD_PARTY.md).

**Streaming di Pokémon Smeraldo da un GBA SP senza modifiche interne al browser del PC, attraverso Raspberry Pi Pico e porta Link.**

[English](README.md) · **Italiano** · [Avvio](PROVA-SMERALDO.md) · [Architettura](docs/ARCHITECTURE.md#italiano)

GBMirroring è un progetto sperimentale hardware/software che mostra sul PC la partita eseguita da una cartuccia reale. Il gioco gira sulla console; un piccolo programma residente esporta lo stato grafico attraverso il cavo Link, e il PC ricostruisce l'immagine per il browser locale e OBS.

**Idea e direzione del progetto: hacke e Lain. Lo sviluppo di GBMirroring è stato effettuato interamente con AI, usando GPT 6 Astra.** Assemblaggio hardware, prove, feedback e decisioni sono contributi umani. Codice e progetti preesistenti restano attribuiti ai rispettivi autori: la dichiarazione sullo sviluppo AI non si riferisce alla loro paternità.

Questa pubblicazione condivide codice funzionante, strumenti pronti e limiti misurati. **La 0.12.0 cambia lo stream in un pacchetto per ogni frame del gioco; è verificata solo con un gioco emulato e il vero codice del residente, non ancora su una console fisica.**

## Cosa funziona

- Streaming da cartuccia reale provato su **GBA SP e Pokémon Smeraldo italiano originale, BPEI revisione 0**.
- Adattatore **Raspberry Pi Pico RP2040** con un solo firmware per multiboot e streaming, senza cambiarlo durante la procedura.
- Applicazione portatile Windows x64 e visualizzatore web locale utilizzabile anche in OBS.
- Cache grafica, aggiornamenti differenziali, verifiche di integrità e recupero automatico. Le copie che il gioco prende dalla propria ROM vengono ripetute dal PC da un'immagine locale della tua cartuccia, creata una volta dalla console (circa tre minuti, solo alla prima volta).
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
| Software | Residente Smeraldo 0.12.1, firmware Pico unificato 0.7.0 |

Non servono modifiche interne alla console. Il profilo attuale usa indirizzi specifici e controlla la revisione della cartuccia. Altre lingue di Smeraldo, Rosso Fuoco/Verde Foglia, giochi GB/GBC e cartucce arbitrarie **non sono supportati da questa release**. Un adattatore o cavo diverso può avere collegamenti differenti.

## Avvio rapido

1. Scarica lo ZIP completo da **Code → Download ZIP** ed estrailo in una cartella scrivibile. Non avviare i BAT dentro lo ZIP.
2. Se il Pico non usa già il nostro firmware unificato 0.7.0, tieni premuto BOOTSEL mentre colleghi USB e copia `dist/gbmirroring-unified-v0.7.0.uf2` nella sua unità. Per questa release basta una volta.
3. **Solo la prima volta:** accendi il GBA senza cartuccia, avvia **14-AVVIA-SMERALDO.bat**, premi **INVIO**, inserisci Smeraldo italiano quando richiesto e premi **A** (non START). La console copia la cartuccia in `runtime/cache/` sul PC in circa tre minuti. Riavvia il GBA quando il PC dice che la cache è stata salvata.
4. Accendi il GBA senza cartuccia. Avvia **14-AVVIA-SMERALDO.bat** e premi **INVIO** per il multiboot.
5. Quando richiesto sulla console, inserisci Smeraldo italiano, premi **START** ed entra nella partita.
6. Quando il PC indica **PRONTO**, premi **SELECT + L + R** sul GBA. Si apre **http://127.0.0.1:8765**. Lascia aperto il BAT.

Il pacchetto comprende Python portatile, librerie USB, renderer, homebrew e UF2 compilati. Non devi compilare, fornire una ROM commerciale al PC o avere la cartella privata di sviluppo.

Per OBS: sorgente Browser **http://127.0.0.1:8765/?clean=1**, 240 × 160 o multipli interi. Il browser mantiene circa 200 ms di buffer. Il visualizzatore attuale non trasmette l'audio del gioco.

[Guida completa, recupero e collaudo →](PROVA-SMERALDO.md)

## Come funziona

Il PC carica via multiboot un piccolo programma in RAM. Il loader verifica la cartuccia e avvia il gioco mantenendo il residente. Questo osserva registri grafici, palette, OAM e VRAM, comprime le modifiche e le invia attraverso i segnali GPIO della porta Link. Il Pico riceve le parole con PIO/DMA e le inoltra via USB CDC. Il PC verifica le transazioni, aggiorna una cache grafica e usa il renderer basato su mGBA per produrre l'immagine mostrata nel browser.

La porta Link non espone un segnale video LCD grezzo. Il PC ricostruisce le risorse esportate dalla console; non esegue una seconda copia del gioco da una ROM commerciale. La 0.12.0 invia un pacchetto per ogni frame del gioco: registri, palette e OAM sempre, più quanti blocchi VRAM cambiati entrano in un piccolo budget di tempo; il resto risulta in coda e segue. Il PC tiene i frame in ordine finché i blocchi in coda arrivano e il buffer da 200 ms del browser assorbe la differenza. Lo scorrimento delle mappe viaggia come una sola coppia di colonne (o di righe) per layer, e le copie dalla ROM come riferimenti di cinque parole confermati parola per parola sul GBA. Il residente lascia priorità al gioco: salta un frame se il gioco è ancora occupato al VBlank. `SELECT + R + A` abbassa la cadenza se la console rallentasse.

## Prestazioni documentate

Tutti i numeri 0.12.0 seguenti vengono dal vero codice del residente con un gioco **emulato** e un modello dei cicli, decodificati dal ricevitore del PC: non sono misure fisiche.

| Evidenza | Risultato | Interpretazione |
|---|---|---|
| Sessione fisica 0.10.0 | 20,16 frame ricevuti/s medi, con forti scatti camminando all'aperto | La media nasconde intervalli molto peggiori |
| 0.12.0 emulata, fermo / cammino / cammino verticale / corsa | 60 frame dello stream ogni 60 del gioco; 96-100% dei frame identici pixel per pixel al frame emulato (fermo 100%, cammino 99%, verticale 97,5%, corsa 96%), secondo peggiore 56-60 frame | Lo stream tiene il passo nel modello; le piccole differenze sono tile che arrivano con qualche frame di ritardo |
| 0.12.0, ciclo principale del gioco emulato con il residente (timing mGBA) | 1197 / 1198 iterazioni camminando e 1197 / 1198 correndo (gioco senza residente 1198) | Il ritmo del gioco è conservato in emulazione; l'audio non è misurato |
| 0.12.0, apertura/chiusura menu emulata | secondi di immagine ferma mentre si ricaricano circa 170 blocchi di tile | I cambi scena sono ancora lenti: limite noto |
| 0.12.0, fisica | **non ancora registrata** | Tempi del Link, audio e presentazione nel browser vanno verificati su una console |

I risultati fisici della 0.11.0 o precedenti non si applicano. Refresh del browser, frame dello stream e fluidità del GBA sono misure separate; frame interpolati o ripetuti non sono mai contati come nuovi frame dello stream.

[Registro hardware](docs/VALIDAZIONE-HARDWARE.md) · [Risultati software](test-results/software-v0.12.0/summary.json) · [Limiti e sviluppo futuro](docs/ARCHITECTURE.md#italiano)

## Origine e crediti

Il lavoro nasce dagli esperimenti di hacke e Lain con adattatori Link, collegamenti online e un progetto separato per giocare insieme a Smeraldo. L'unione delle repository è prevista in futuro. **Il software cooperativo non è attualmente incluso né presentato come una funzione di GBMirroring.**

Ringraziamenti a [agtbaskara](https://github.com/agtbaskara/game-boy-pico-link-board) per la scheda, [Celio-Link](https://github.com/Celio-Link) per il trasporto e la sequenza PIO da cui deriva il multiboot, agli autori dei moduli `mb_multi.py` e `usb_link.py` forniti al progetto, a [pret/pokeemerald](https://github.com/pret/pokeemerald) per le strutture del gioco, a [mGBA](https://github.com/mgba-emu/mgba) per il renderer e a Pico SDK, TinyUSB, Python, PyUSB e libusb.

[THIRD_PARTY.md](THIRD_PARTY.md) documenta attribuzioni e distribuzione. Nessuna ROM commerciale o salvataggio è incluso. Pokémon e Nintendo identificano la compatibilità; il progetto è indipendente, non affiliato né approvato dai titolari. La pubblicazione documenta il lavoro e la sua cronologia, senza rivendicare esclusività o priorità su altri progetti.

## Orientarsi e contribuire

`firmware/emerald-stream` contiene il residente corrente (`emerald-columns` è la baseline 0.11.0); `firmware/unified` il firmware Pico; `tools` launcher, protocolli e test; `native/renderer` l'adattatore del renderer e i sorgenti mGBA corrispondenti; `runtime` le dipendenze portatili; `dist` i binari versionati; `test-results` le evidenze selezionate; `docs` le guide.

Per una segnalazione indica versione, adattatore/cavo, lingua e revisione della cartuccia, scena e comportamento sul GBA. Controlla i rapporti prima di caricarli: i log grezzi possono contenere percorsi locali o identificativi dei dispositivi. Non allegare ROM o salvataggi. Vedi [CONTRIBUTING.md](CONTRIBUTING.md#italiano).
