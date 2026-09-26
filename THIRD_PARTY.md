# Third-party notices / Componenti di terzi

## English

Project-owned GBMirroring code is GPL-3.0 (LICENSE). Dependencies retain their licenses. Concept and direction: hacke & Lain; GBMirroring development entirely with GPT 6 Astra, with human assembly, decisions and tests. This does not claim AI authorship of third-party code.

| Component | Origin / authors | License, notices and corresponding source |
|---|---|---|
| Master PIO in firmware/multi-profile and firmware/unified | Celio-Link / Celio-Firmware contributors, including [Exormeter](https://github.com/Exormeter) | GPL-3.0. Pinned unmodified reference, license and hash in vendor/celio_reference. All 27 words verified; GBMirroring adds its own Pico SDK control and streaming logic. |
| vendor/celio_transport Python modules | Supplied gen3-poke-multiplayer project; USB logic based on Celio-Client/Server | GPL-3.0 declared in supplied archive; contributor permission received. Source included unchanged; see directory README. |
| Historical recovery UF2 | Celio-Firmware contributors, supplied project modifications and pre-existing modifications of unidentified individual authorship | GPL-3.0 declared by supplier. Base source, complete patch and build recipe in vendor/celio_legacy_source. See docs/CELIO-PUBLICATION-AUDIT.md for limits. Not used by current streaming launcher. |
| Python 3.13.3 | Python Software Foundation and contributors | PSF and incorporated notices: runtime/python/LICENSE.txt. [Source](https://www.python.org/downloads/release/python-3133/). Executables unmodified. |
| PyUSB 1.3.1 | PyUSB contributors, including Wander Lairson Costa | BSD-3-Clause: licenses/PyUSB-BSD-3-Clause.txt. Python source included; [upstream](https://github.com/pyusb/pyusb/tree/v1.3.1). |
| libusb-package 1.0.30.0 | PyOCD/libusb-package contributors | Apache-2.0: licenses/libusb-package-Apache-2.0.txt. Wrapper source included; [upstream](https://github.com/pyocd/libusb-package). |
| libusb 1.0.30 DLL | libusb contributors | LGPL-2.1: licenses/libusb-LGPL-2.1.txt. [Complete source](https://github.com/libusb/libusb/tree/v1.0.30). Separately loaded DLL; users may replace/rebuild it. |
| importlib_resources | Python importlib_resources contributors, including Jason R. Coombs | Apache-2.0: licenses/importlib-resources-Apache-2.0.txt. Supplied Python sources included; exact release unidentified. Do not claim byte identity with 6.5.2. [Upstream](https://github.com/python/importlib_resources). |
| mGBA libretro core | mGBA contributors | MPL-2.0: runtime/mgba/LICENSE. Version 0.11-219-e31759b; [source](https://github.com/libretro/mgba/tree/e31759b24e7a4e3899285ff720d7b573ac328ae7). Binary manifest included. |
| Native mGBA renderer units | mGBA contributors | MPL-2.0: runtime/native/LICENSE-mgba.txt. Unmodified required units/headers in native/renderer/mgba-source.zip, same commit above. Our bridge: native/renderer/renderer.c; build: tools/build_native_renderer.py. |
| Pico SDK 2.2.0 | Raspberry Pi (Trading) Ltd. and contributors | BSD-3-Clause and component notices: licenses/Pico-SDK-BSD-3-Clause.txt; [complete pinned source](https://github.com/raspberrypi/pico-sdk/tree/2.2.0). |
| TinyUSB | Ha Thach and contributors | MIT: licenses/TinyUSB-MIT.txt; [pinned source](https://github.com/hathach/tinyusb/tree/86ad6e56c1700e85f1c5678607a762cfe3aa2f47). Derived descriptor files preserve original headers. |

The legacy Celio binary also incorporates Zephyr and HAL components. Pinned sources and build dependencies are documented beside its application source. Original per-file notices remain authoritative; this table does not replace them. Source preparation downloads are pinned by tools/prepare_dependencies.py.

DLL integrity checks are diagnostics, not restrictions on modifying LGPL/MPL components. For your own compatible rebuilt dependency, update its manifest hash or adapt the included checker source. No additional restriction on modification or debugging is imposed.

### References and development tools

- [agtbaskara/game-boy-pico-link-board](https://github.com/agtbaskara/game-boy-pico-link-board): hardware reference; no PCB design files redistributed here.
- [GBATEK](https://problemkaputt.de/gbatek.htm), Martin Korth: hardware documentation.
- [pret/pokeemerald](https://github.com/pret/pokeemerald): game-interface research, structures and addresses. Its game material is not treated as GPL assets.
- Supplied project credits [afska/gba-link-connection](https://github.com/afska/gba-link-connection) and [Lorenzooone/PokemonGB_Online_Trades_and_Battles](https://github.com/Lorenzooone/PokemonGB_Online_Trades_and_Battles) as multiboot references, not copied Python modules.
- Ninja (Apache-2.0), GNU Arm toolchain and Unicorn are build/test dependencies, not bundled user-runtime components.

### Game material and import scope

The 156-byte Nintendo boot logo in vendor/celio_transport/logo.bin and compiled GBA homebrew is required by the BIOS; it is not project-owned GPL artwork. Test screenshots retain the underlying game's rights. Names and images identify compatibility/results, without endorsement. No commercial ROMs, saves or complete game-asset packs are included.

Only necessary transport and corresponding firmware source material are imported from the friend's archive. Its separate firmware implementation, cooperative payload, Lua libraries, web-map icons and other release binaries are not imported. Their presence in the input archive does not make them GBMirroring features or dependencies.

## Italiano

Il codice proprio GBMirroring usa GPL-3.0; le dipendenze mantengono le proprie licenze. Idea e direzione: hacke & Lain. Sviluppo GBMirroring interamente con GPT 6 Astra, con assemblaggio, prove e decisioni umane. Non attribuiamo all'AI il codice di terzi.

La tabella sopra elenca autori, componenti, licenze e sorgenti. Testi completi nelle cartelle licenses, runtime e negli archivi sorgente. Le 27 parole PIO Celio sono verificate contro una copia fissata. I moduli ricevuti conservano paternità e GPL dichiarata dal progetto fornito.

Per il vecchio UF2 sono inclusi base e patch completa. Il binario ricevuto è identico a quello storico; tutte le patch si applicano. Una ricompilazione identica non è stata verificata. Tre modifiche erano documentate come preesistenti, senza autore identificato: non le attribuiamo a voi. Dettagli in vendor/celio_legacy_source e nel registro di audit.

libusb è una DLL separata sostituibile; sorgente e LGPL sono indicati. Anche i componenti MPL restano modificabili secondo licenza. Chi ricompila una dipendenza può aggiornare manifest e verificatore forniti nei sorgenti: i controlli non vietano la modifica.

Logo BIOS e screenshot del gioco non diventano opere GPL del progetto. Nessuna ROM commerciale, salvataggio, raccolta di asset o icona della mappa del progetto amico è inclusa. Cooperativa e dipendenze non necessarie non sono state importate. Restano autorevoli gli avvisi originali dei singoli file. I riferimenti hardware e di ricerca non implicano redistribuzione dei rispettivi progetti.
