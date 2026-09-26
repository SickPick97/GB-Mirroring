# Architecture / Architettura

## English

The game runs on the real cartridge and console. Multiboot first installs a small resident in GBA RAM; a cartridge-specific hook lets it observe graphics state while the game continues. This is not capture of an electrical LCD signal and not a second game instance on the PC.

The resident exports display registers, palette, OAM and changed VRAM blocks. It spreads its work across game updates, with a bounded transfer budget (155 words per intervention in 0.11.0). The current resident is 4160 bytes; its loader is 5824 bytes. These figures describe program size, not free memory available to arbitrary games. The Italian Emerald profile and reserved RAM assumptions must be revalidated for each additional cartridge.

The Pico runs one firmware for both multiboot and Link receive mode. Its boot PIO sequence derives from Celio. The streaming protocol, graphics cache, packet checks and compression are implemented in this repository. USB CDC carries the packets to the Windows host. The host validates and updates its cache, then renders graphics through the mGBA software renderer. A local WebSocket viewer buffers about 200 ms to improve presentation regularity.

The renderer's display refresh, received graphics snapshots and GBA gameplay rate are different measurements. Repeated images are not evidence of new game frames. CRC/hash checks detect corruption but do not make a snapshot collected over several interventions temporally atomic. Scanline-dependent effects are incomplete.

| Component | Source / build entry |
|---|---|
| Current GBA resident | `firmware/emerald-columns/`; builders under `tools/` |
| Pico firmware | `firmware/unified/` |
| Boot and host capture | `tools/start_unified.py`, `tools/sd_video_viewer.py` |
| Supplied multiboot transport | `vendor/celio_transport/` |
| Native graphics renderer | `native/renderer/`, `tools/build_native_renderer.py` |
| Build dependencies | `tools/prepare_dependencies.py` (pinned downloads and hashes) |
| Legacy Celio recovery source | `vendor/celio_legacy_source/` (separate from current Pico firmware) |

Keep versioned binaries immutable. The current package contains resident 0.11.0 and Pico firmware 0.7.0; documentation changes do not imply a new firmware. Offline checks: `runtime/python/python.exe tools/check_portable.py`, `python tools/verify_celio_provenance.py`. These commands do not communicate with a console. Development builds require the appropriate ARM toolchain and pinned dependencies; users run the supplied binaries.

## Roadmap

The target remains a sustained 30 new stream frames/s during movement while preserving GBA gameplay. Outdoor tilemap traffic and scene changes still exceed the desired budget. The latest codec reduces some scrolling traffic, but does not solve all scenes. Future work must compare the same physical scene, measure received and presented intervals separately, and preserve recovery correctness. Other game profiles and cooperative-project integration are future work, not current features.

## Italiano

Il gioco gira sulla cartuccia e sulla console reali. Il multiboot installa un piccolo residente in RAM; un hook specifico della cartuccia gli permette di osservare lo stato grafico durante il gioco. Non si acquisisce il segnale elettrico dello schermo e il PC non esegue una seconda partita.

Il residente invia registri video, palette, OAM e blocchi VRAM cambiati. Distribuisce il lavoro su più aggiornamenti, con limite di 155 parole per intervento nella 0.11.0. Il residente occupa 4160 byte e il loader 5824 byte: non sono una misura della RAM libera per giochi generici. Profilo italiano e zone RAM riservate richiedono verifiche per ogni nuova cartuccia.

Un solo firmware Pico gestisce multiboot e ricezione. La sequenza PIO di avvio deriva da Celio. Protocollo streaming, cache grafica, controlli e compressione sono nel progetto. USB CDC porta i pacchetti al PC, che verifica la cache e ricostruisce l'immagine usando il renderer software mGBA. La pagina locale usa WebSocket e circa 200 ms di buffer.

Refresh del browser, snapshot ricevuti e fluidità del gioco sono misure diverse. Ripetere un'immagine non produce nuovi frame del gioco. CRC e firme rilevano corruzione, ma uno snapshot raccolto in più interventi non diventa per questo istantaneo. Gli effetti per scanline sono incompleti.

La tabella sopra identifica i sorgenti. I controlli offline indicati non comunicano con la console. Gli utenti usano i binari pronti; compilare richiede toolchain ARM e dipendenze fissate. Non sostituire un binario pubblicato mantenendo la stessa versione.

L'obiettivo resta 30 nuovi frame al secondo durante il movimento, preservando il GBA. Il traffico delle mappe esterne e i cambi scena rimangono limitanti; l'ultimo codec migliora alcuni casi senza risolverli tutti. Occorrono confronti nella stessa scena fisica e misure separate di ricezione e presentazione. Altri giochi e integrazione cooperativa restano sviluppi futuri.
