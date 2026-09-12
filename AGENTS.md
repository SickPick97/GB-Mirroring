# Collaborazione GBMirroring

- Lingua dell'utente: italiano. Scopo finale aggiornato il 2026-09-12: GBA SP senza modifiche interne, Pico RP2040, streaming fluido su pagina web locale curata. Webcam USB autonoma non piu richiesta dall utente. Il loader potra riconoscere profili di cartuccia progressivamente.
- Leggere README.md, CHANGELOG.md e docs/VALIDAZIONE-HARDWARE.md prima di proseguire. Non confondere prove software, UVC sintetico e cattura reale dalle cartucce.
- Mantenere portatili percorsi e BAT. Il runtime utente e runtime/python; i moduli preesistenti sono vendor/celio_transport. Non rendere necessaria PROGETTO AMICO per avviare i test.
- Non modificare i moduli originali sotto vendor senza motivazione documentata. Non includere ROM commerciali, salvataggi, credenziali o materiali estranei nei commit.
- Per ogni aggiornamento completato aggiornare il changelog e i test pertinenti, quindi creare un commit descrittivo. Sincronizzare con la repository privata autorizzata quando l'accesso e disponibile; evitare force push o riscritture della cronologia.
- Per ogni risultato hardware fornito, analizzare log e immagini, aggiornare il registro, e conservare solo evidenza selezionata e ripulita in test-results. I log grezzi restano locali salvo richiesta esplicita.
- Non sovrascrivere una release pubblicata o cambiare un UF2 mantenendo la stessa versione. Distinguere versione pacchetto e firmware. Consegnare binari pronti e istruzioni per l'utente, che non deve compilare.
- I flash dei dispositivi vengono effettuati fisicamente dall'utente seguendo la guida. Non caricare firmware o iniziare trasmissioni Link solo per verificare la repository.
