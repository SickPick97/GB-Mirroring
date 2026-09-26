# Supplied multiboot transport / Trasporto ricevuto

## English

mb_multi.py and usb_link.py were supplied by the contributors of gen3-poke-multiplayer. Their source archive declares GPL-3.0 and redistribution was explicitly authorized. The original GBMirroring copies are unchanged.

usb_link.py is byte-identical to the new archive. The newer mb_multi.py adds a 0.5-second delay and comments before its legacy command-line reboot. This update is not imported: publication preparation preserves tested boot behavior. Our older module is distributed as source, not described as identical to the newer file.

The supplied notices attribute USB device/session logic to Celio-Client and Celio-Server, and credit afska/gba-link-connection and Lorenzooone/PokemonGB_Online_Trades_and_Battles as multiboot references. See root THIRD_PARTY.md and LICENSE. These are not original GBMirroring modules.

logo.bin is the 156-byte Nintendo boot-header logo extracted from supplied homebrew, required by the BIOS. It is not a commercial game ROM, the cooperative payload or project-owned GPL artwork.

## Italiano

I moduli provengono da gen3-poke-multiplayer, il cui archivio dichiara GPL-3.0; redistribuzione autorizzata dai responsabili. Le copie già usate da GBMirroring restano invariate.

usb_link.py coincide con il nuovo archivio. Il nuovo mb_multi.py aggiunge attesa di mezzo secondo e commenti prima del riavvio CLI del vecchio firmware: non importiamo questo cambiamento durante la preparazione della pubblicazione. Il nostro modulo precedente è incluso integralmente come sorgente.

Gli avvisi ricevuti attribuiscono la logica USB a Celio-Client/Server, con afska e Lorenzooone come riferimenti multiboot. Il logo BIOS di 156 byte non è grafica propria del progetto né una ROM commerciale.
