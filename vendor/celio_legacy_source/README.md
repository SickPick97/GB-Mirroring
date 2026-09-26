# Legacy Celio recovery firmware source / Sorgenti firmware Celio storico

## English

This directory supplies the upstream application source and complete patch identified by the contributor as the source of `dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2` (firmware 2.0.5). It is **not** the current GBMirroring unified streaming firmware. Source and binary hashes are recorded in `provenance.json`.

- Upstream: [Celio-Link/Celio-Firmware](https://github.com/Celio-Link/Celio-Firmware/tree/f67733c293defc3d77185101cb00d3ce19ef3284), commit `f67733c293defc3d77185101cb00d3ce19ef3284`, GPL-3.0. Its unmodified archive is included as `upstream.zip` with its original license and notices.
- `modifications.patch`: received from the authors of `gen3-poke-multiplayer`, whose supplied project declares GPL-3.0. Dated 2026-08-02 in their documentation. Includes raw timing, zero-word/variable USB packet handling, back-pressure, cable selection and software reboot changes.
- The contributor's documentation explicitly identifies three pre-existing modifications in `usbLinkCommand.cpp`, `usbSection.hpp` and raw-relay drop counters. Their individual authors are **not identified** in the supplied material. Do not attribute these to hacke, Lain or the AI used for GBMirroring. Their licensing is reported from the supplier's GPL declaration, not independently established authorship.
- The supplied release UF2 matches our historical UF2 byte-for-byte. All 11 file patches apply to the pinned base. This is source-provenance evidence, **not a reproducible-binary build claim**.

## Recover the application source (offline)

Run `python tools/prepare_legacy_celio_source.py`. Requires Python and Git, not a connected device. It verifies all hashes, extracts a fresh source tree under ignored `build/legacy-celio/`, applies the patch and verifies the changed files. It refuses to overwrite an existing output directory.

## Build environment

The supplier built for Zephyr board `rpi_pico`, using GNU Arm Embedded **14.3 rel1**, `ZEPHYR_TOOLCHAIN_VARIANT=gnuarmemb`, and `CONFIG_REBOOT=y` in the patched `prj.conf`. The binary identifies Zephyr `v3.7.2-5-g41c0a2e3744c`, resolving to [41c0a2e3744cb9b048d2bc3f244f41c9f4726fcc](https://github.com/zephyrproject-rtos/zephyr/tree/41c0a2e3744cb9b048d2bc3f244f41c9f4726fcc). The original Celio `west.yml` follows `v3.7-branch`; pin this commit when reconstructing this historical environment instead of following today's branch.

That Zephyr revision pins [CMSIS 4b96cbb174678dcd3ca86e11e1f24bc5f8726da0](https://github.com/zephyrproject-rtos/cmsis/tree/4b96cbb174678dcd3ca86e11e1f24bc5f8726da0) and [hal_rpi_pico fba7162cc7bee06d0149622bbcaac4e41062d368](https://github.com/zephyrproject-rtos/hal_rpi_pico/tree/fba7162cc7bee06d0149622bbcaac4e41062d368). These are manifest-derived dependency revisions; the supplier did not provide a frozen `west manifest --freeze` or ELF. Original dependency sources and notices are available at those pinned links. Zephyr/CMSIS contain Apache-2.0 components; Pico HAL contains BSD-licensed components and additional per-file notices.

Copies of the root dependency licenses are included in `licenses/Zephyr-Apache-2.0.txt`, `licenses/CMSIS-Apache-2.0.txt` and `licenses/Pico-HAL-BSD-3-Clause.txt` at the project root. Preserve additional notices when downloading or redistributing their complete source trees.

In a prepared Zephyr workspace, set `ZEPHYR_BASE` to that Zephyr checkout and `GNUARMEMB_TOOLCHAIN_PATH` to your compiler installation. Build the patched application with:

```powershell
west build -b rpi_pico -d build/legacy-celio-build build/legacy-celio
```

Output: `build/legacy-celio-build/zephyr/zephyr.uf2`. This is a developer recipe based on supplied build instructions, not a newly validated firmware. Do not replace a published UF2 under its old version; do not flash it to run the current streaming launcher.

## Italiano

Questa cartella contiene sorgenti upstream e patch completa indicati dal contributore per il vecchio UF2 Celio 2.0.5. Non è il firmware unificato attuale. Hash e provenienza sono in `provenance.json`; licenza GPL-3.0 e avvisi originali sono conservati.

L'UF2 ricevuto coincide esattamente con quello storico; la patch si applica a tutti gli 11 file sulla base fissata. Non abbiamo ricompilato e confrontato il binario. Le tre modifiche preesistenti indicate sopra non hanno un autore identificato nei documenti ricevuti: non le attribuiamo a voi né all'AI. La dichiarazione GPL proviene dal progetto fornito, non da una verifica indipendente della loro paternità.

`python tools/prepare_legacy_celio_source.py` ricostruisce offline i sorgenti in `build/legacy-celio`, controllando gli hash e senza sovrascrivere cartelle esistenti. Richiede Python e Git, non hardware. Per compilare servono toolchain e workspace Zephyr descritti sopra. Il commit Zephyr viene dalla stringa del binario, le revisioni CMSIS/HAL dal suo manifest: manca un manifest congelato originale. La ricetta non certifica una nuova build e non richiede alcun flash per usare lo streaming attuale.
