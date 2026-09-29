# Architecture / Architettura

## English

The game runs on the real cartridge and console. Multiboot first installs a small resident in GBA RAM; a cartridge-specific hook lets it observe graphics state while the game continues. This is not capture of an electrical LCD signal and not a second game instance on the PC.

Since 0.12.0 the resident sends **one packet per game VBlank**: registers, palette and OAM every time, plus as many changed VRAM blocks as fit in a small time budget. Blocks that did not fit stay pending and are reported in the packet, so the PC orders its playout instead of waiting for a global transaction. Copies that the game takes from its own ROM (tile animations, sprite frames) are not sent as pixels: the resident confirms, word by word, that VRAM holds those ROM bytes and sends a five-word reference; the PC replays the copy from a local image of your own cartridge, created once by the GBA dump mode. The PC never runs the game and needs no ROM you provide. See [PROTOCOLLO-STREAM.md](PROTOCOLLO-STREAM.md) (Italian) for the packet layout.

The resident lets the game go first: it does not run when the game is still busy at VBlank, it stops bulk work after a small number of scanlines, and it never delays registers, palette and OAM. `SELECT + L + R` toggles capture; `SELECT + R + A` cycles the cadence (every VBlank, every 2nd, every 3rd) if the console ever shows game slowdown. The resident is about 5.1 KB and the loader 8.8 KB; these describe program size, not free memory available to arbitrary games. The Italian Emerald profile and reserved RAM assumptions must be revalidated for each additional cartridge.

The Pico runs one firmware for both multiboot and Link receive mode. Its boot PIO sequence derives from Celio. The streaming protocol, graphics cache, packet checks and compression are implemented in this repository. USB CDC carries the packets to the Windows host. The host validates and updates its cache, holds frames in order while blocks are pending, then renders graphics through the mGBA software renderer. A local WebSocket viewer buffers about 200 ms to absorb bursts.

The renderer's display refresh, received graphics snapshots and GBA gameplay rate are different measurements. Repeated images are not evidence of new game frames. A frame that had to be released while blocks were still pending uses the newest VRAM for those blocks. Scanline-dependent effects are incomplete.

| Component | Source / build entry |
|---|---|
| Current GBA resident | `firmware/emerald-stream/`; `tools/build_emerald_stream.py` |
| Previous resident (baseline) | `firmware/emerald-columns/` (0.11.0) |
| Pico firmware | `firmware/unified/` |
| Boot and host capture | `tools/start_unified.py`, `tools/sd_video_viewer.py`, `tools/stream_parser.py`, `tools/rom_cache.py` |
| Supplied multiboot transport | `vendor/celio_transport/` |
| Native graphics renderer | `native/renderer/`, `tools/build_native_renderer.py` |
| Build dependencies | `tools/prepare_dependencies.py` (pinned downloads and hashes) |
| Development co-simulation | `tools/cosim_stream.py` (game in mGBA, real ARM resident in Unicorn, PC parser) |
| Legacy Celio recovery source | `vendor/celio_legacy_source/` (separate from current Pico firmware) |

Keep versioned binaries immutable. The current package contains resident 0.12.0 and Pico firmware 0.7.0. Offline checks: `runtime/python/python.exe tools/check_portable.py`, `python tools/verify_celio_provenance.py`. These commands do not communicate with a console. Development builds require the appropriate ARM toolchain and pinned dependencies; users run the supplied binaries.

## Roadmap

The 0.12.0 stream is verified only in software: with an emulated game and the real resident code it publishes one frame per VBlank while standing, walking and running, and the emulated main loop of the game keeps its pace within about one frame per twenty seconds of the unmodified game. A physical test has not been recorded. Known limits: scene loads (leaving a menu, entering a building) still send new tile data at about one block per VBlank and take seconds; running scrolls the map faster than the budget can always follow; scanline effects are incomplete. Planned direction: identify decompressed graphics from the cartridge image so scene loads become references, and finer map-column patches. Other game profiles and cooperative-project integration are future work, not current features.

## Italiano

Il gioco gira sulla cartuccia e sulla console reali. Il multiboot installa un piccolo residente in RAM; un hook specifico della cartuccia gli permette di osservare lo stato grafico durante il gioco. Non si acquisisce il segnale elettrico dello schermo e il PC non esegue una seconda partita.

Dalla 0.12.0 il residente invia **un pacchetto per ogni VBlank**: registri, palette e OAM sempre, piu quanti blocchi VRAM cambiati entrano in un piccolo budget di tempo. I blocchi rimasti restano in coda e il pacchetto lo dichiara, quindi il PC ordina la presentazione invece di attendere una transazione globale. Le copie che il gioco prende dalla propria ROM (animazioni dei tile, frame degli sprite) non viaggiano come pixel: il residente conferma parola per parola che la VRAM contiene quei byte di ROM e invia un riferimento di cinque parole; il PC ripete la copia da un'immagine locale della tua cartuccia, creata una volta dal modo copia del GBA. Il PC non esegue il gioco e non serve una ROM fornita da te. Il formato e in [PROTOCOLLO-STREAM.md](PROTOCOLLO-STREAM.md).

Il residente lascia priorita al gioco: non lavora se il gioco e ancora occupato al VBlank, interrompe il lavoro sui blocchi dopo poche righe di scansione e non ritarda mai registri, palette e OAM. `SELECT + L + R` attiva o ferma la cattura; `SELECT + R + A` cambia la cadenza (ogni VBlank, uno su due, uno su tre) se la console mostrasse rallentamenti del gioco. Il residente occupa circa 5,1 KB e il loader 8,8 KB: non sono una misura della RAM libera per giochi generici. Profilo italiano e zone RAM riservate richiedono verifiche per ogni nuova cartuccia.

Un solo firmware Pico gestisce multiboot e ricezione. La sequenza PIO di avvio deriva da Celio. Protocollo streaming, cache grafica, controlli e compressione sono nel progetto. USB CDC porta i pacchetti al PC, che verifica la cache, tiene i frame in ordine finche restano blocchi in coda e ricostruisce l'immagine usando il renderer software mGBA. La pagina locale usa WebSocket e circa 200 ms di buffer per assorbire le raffiche.

Refresh del browser, snapshot ricevuti e fluidita del gioco sono misure diverse. Ripetere un'immagine non produce nuovi frame del gioco. Un frame rilasciato mentre alcuni blocchi erano ancora in coda usa la VRAM piu recente per quei blocchi. Gli effetti per scanline sono incompleti.

La tabella sopra identifica i sorgenti. I controlli offline indicati non comunicano con la console. Gli utenti usano i binari pronti; compilare richiede toolchain ARM e dipendenze fissate. Non sostituire un binario pubblicato mantenendo la stessa versione.

Lo stream 0.12.0 e verificato solo in software: con un gioco emulato e il vero codice del residente pubblica un frame per VBlank da fermo, camminando e correndo, e il ciclo principale emulato del gioco resta entro circa un frame ogni venti secondi rispetto al gioco senza residente. Non e registrata una prova fisica. Limiti noti: i caricamenti di scena (uscita da un menu, ingresso in un edificio) inviano ancora dati nuovi a circa un blocco per VBlank e durano secondi; la corsa fa scorrere la mappa piu in fretta di quanto il budget riesca sempre a seguire; gli effetti per scanline sono incompleti. Direzione prevista: riconoscere dalla cartuccia la grafica decompressa, cosi i caricamenti diventano riferimenti, e patch di colonna piu fini. Altri giochi e integrazione cooperativa restano sviluppi futuri.
