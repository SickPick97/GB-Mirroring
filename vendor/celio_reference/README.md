# Celio source reference / Riferimento sorgente Celio

**English.** `linkLayer_pio.c` is an unmodified source reference from Celio-Firmware, pinned in `upstream.json`, under GPL-3.0. It is included to document and verify the 27-word GBA master PIO sequence used in `firmware/multi-profile/main.c` and `firmware/unified/pico.c`. It is not compiled as a Zephyr driver by GBMirroring. The surrounding Pico SDK integration and USB protocol are GBMirroring adaptations. Attribution: Celio-Link/Celio-Firmware contributors, https://github.com/Celio-Link/Celio-Firmware. Original notices and the complete license are preserved.

Run `python tools/verify_celio_provenance.py` to compare the words without accessing hardware. This proves the source relationship of the PIO sequence; it does not identify the source of the separate historical Celio recovery UF2.

**Italiano.** `linkLayer_pio.c` è un riferimento sorgente invariato di Celio-Firmware, fissato in `upstream.json`, sotto GPL-3.0. Documenta e verifica le 27 istruzioni PIO master GBA usate nei due firmware indicati. GBMirroring non compila questo driver Zephyr: integrazione Pico SDK e protocollo USB sono adattamenti del progetto. Attribuzione agli autori di Celio-Link/Celio-Firmware; avvisi originali e licenza completa conservati.

Il verificatore confronta le istruzioni senza accedere all'hardware. Non identifica i sorgenti del distinto UF2 storico di ripristino Celio.
