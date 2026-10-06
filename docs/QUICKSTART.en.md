# Quick start

[Italian instructions](../PROVA-SMERALDO.md) · [Project overview](../README.md)

## Requirements

Windows 10/11 x64, a USB data cable, an RP2040 Pico Link adapter and the tested GBA Link cable. The current cartridge profile is **original Italian Emerald, BPEI revision 0**, on GBA SP. Extract the complete package into a writable folder; keep `runtime`, `vendor`, `tools` and `dist` together. The PC never needs a ROM file you supply: the first run copies your own cartridge once (see below).

## One-time firmware installation

Hold BOOTSEL on the Pico while connecting USB. Copy `dist/gbmirroring-unified-v0.8.0.uf2` to the `RPI-RP2` drive. The adapter reboots automatically. Skip this if that exact firmware is already installed. Flashing is performed by you; the launcher does not flash the Pico.

Use the same cable orientation throughout: smaller connector at the adapter, larger connector at the GBA, selector at GBA. No cable reversal or mid-session firmware change is required.

## First run only: copy your cartridge

The 0.12 stream replays many graphics copies from the game's own ROM, so the PC keeps a local image of your cartridge in `runtime/cache/` (never committed or shared). It takes about three minutes and is done once.

1. Start the GBA without a cartridge. Run `14-AVVIA-SMERALDO.bat` and press **Enter** at `INVIO per multiboot`.
2. On the handheld insert your Emerald cartridge and press **A** (not START). A progress bar appears; the PC prints the percentage.
3. When the PC reports `Cache ROM salvata`, close the BAT, restart the GBA (power off and on, no cartridge) and continue with the next section.

If the copy stops or reports a mismatch, delete `runtime/cache` and repeat. Only the Italian BPEI revision 0 cartridge is accepted.

## Start a session

1. Start the GBA without a cartridge. Connect the adapter to the PC and console.
2. Run `14-AVVIA-SMERALDO.bat`. Its offline package check should report `OK`.
3. At `INVIO per multiboot`, press **Enter**. This loads the 0.14.0 resident. After a session press **Scarica log** in the page: it downloads a single zip with all logs to send. `R` resumes a resident already running; `B` selects the older 0.11.0 comparison baseline (no cartridge copy needed).
4. Follow the handheld prompt: insert your Emerald cartridge and press **START**. Enter the game.
5. When the PC reports `PRONTO` (ready), press **SELECT + L + R** to enable capture. This combination toggles capture, so do not repeatedly press it while waiting for the initial image. The first image appears after a few seconds while the PC receives the initial graphics.
6. Open **http://127.0.0.1:8765** if the viewer does not open automatically. Keep the BAT window running.

For OBS use a Browser Source at **http://127.0.0.1:8765/?clean=1**, 240 × 160 or an integer multiple. Audio remains on the GBA; this release does not capture it.

## Recovery and reports

If the host closes but the GBA game and resident are still running, restart the BAT and choose `R`. After resetting or powering off the GBA, perform multiboot again. Do not use the old Celio recovery UF2 for the current streaming launcher.

If the viewer stays blank, first check the BAT for an error, whether the resident was loaded, and whether capture is enabled. Do not replace the tested cable setup as the first troubleshooting step. Local reports are saved under `dist/emerald-reports`. Report the package version, cartridge, scene and exact error. Review logs before sharing; omit device identifiers and personal paths. Never upload ROMs, cartridge images or saves.

## What to expect

This is an experimental release. Software measurements with an emulated game and the real resident code show one published frame per game frame while standing and walking, but a physical test has not been recorded yet: real link timing, audio and browser presentation must be verified on your console. See the README for separate hardware and emulator evidence. Existing console prompts and historical diagnostic BAT files remain in Italian; the steps above cover the current supported entry point.
