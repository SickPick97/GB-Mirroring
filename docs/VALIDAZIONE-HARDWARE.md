**Riscontri sul dispositivo dell'utente**

2026-09-09, firmware gbmirroring-uvc-test-v0.1.0.uf2, Pico RP2040:

- L'utente conferma visualizzazione in Fotocamera di Windows e contatore in avanzamento.
- Screenshot fornito: risoluzione dichiarata 240x160, 10 FPS negoziati, FRAME 105, RETRY 0.
- Chiusura e riapertura di Fotocamera: l'utente conferma ripresa dal contatore precedente. Comportamento previsto a Pico alimentato.
- Non ancora confermati test di durata di 10 minuti e scollegamento/ricollegamento USB.

Questa evidenza riguarda l'uscita UVC sintetica; non comprende cattura dal GBA.

Banco Link 0.2.0: prova fisica ricevuta dall'utente, cartella dist/link-reports/20260909-155556-208260. Esito PASS.

- Multiboot di 2128 byte completato in 3,81 secondi, senza desync o riavvii del protocollo; CRC 0x190F. Il successivo riavvio USB del Pico ha consentito la misura.
- Tutte le cinque finestre di circa 20 secondi sono pulite: nessun errore CRC o pattern, pacchetto mancante o duplicato, incremento di errori seriali. Challenge ricevuti correttamente.
- Payload verificato: timing 7400 = 396,8 B/s; 3700 = 736,0 B/s; 2000 = 1190,3 B/s; 1000 = 1868,7 B/s; 500 = 2623,9 B/s. Sono misure end-to-end del banco Celio multiplayer, non il limite assoluto del Link.
- Screenshot completo, 600 blocchi, zero errori CRC, in 41,08 secondi al timing conservativo 1000. BMP 240x160 ispezionato: testo, barre e indicatore corretti. SHA-256: 6709d15086927c7e9b068312b2be691de2ccabd84da3a363765835eceeef4a18.
- Nessun tasto registrato nelle cinque finestre (keys_seen_mask=0): la prova non conferma ancora la ricezione di pressioni A/B.

Confermato trasferimento della VRAM del nostro homebrew dal GBA al PC. Non ancora verificati streaming continuo, trasporto normal mode, cattura dalle cartucce o integrazione di questa sorgente con UVC. A 2623,9 B/s, 76800 byte di un frame grezzo richiederebbero circa 29,3 secondi, senza ulteriori costi: serve aumentare il throughput e/o ridurre i dati trasmessi.

Banco normal mode 0.3.0: software e firmware preparati, verifica software completata. Prova fisica a 256 kHz e 2 MHz ancora da eseguire; procedura in PROVA-NORMAL.md.

2026-09-09, Normal 0.3.0: utente conferma GBA in trasmissione dopo A e successivo messaggio per B, mentre PC resta PRONTO. Nessun pacchetto riconosciuto visibile. Cavo sempre GBA (correzione dell'ipotesi GBC precedente). Causa ancora da identificare. Ricevitore diagnostico 0.3.2 da collaudare.

2026-09-10: log Normal 0.3.2 confermano 290664 parole (fase completa attesa), nessun header, nessun CRC verificato, nessuno stall PIO segnalato. Primi quattro campioni e ultimo campione di ogni rilevazione tutti zero; non e una cattura di tutte le parole. Ipotesi: GP1 non e la linea dati corretta con il cavo GBA. Versione 0.3.3 ascolta GP3/SD; esito hardware ancora da verificare. Evidenza ripulita in test-results/2026-09-10-normal-v0.3.2/summary.json.
