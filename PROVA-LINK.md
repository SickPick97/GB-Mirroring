**Seconda prova: dati e immagine dal GBA SP al PC**

Questa prova usa il firmware Celio del pacchetto originale e un nuovo homebrew GBMirroring. Il caricatore, il test delle velocita e la cattura sono avviati da un solo file BAT. Python e le librerie USB sono inclusi in runtime/python: non devi installare o compilare nulla.

Il programma gira nella RAM del GBA, con **slot cartuccia vuoto per tutta la prova**. Non avvia Smeraldo o Verde Foglia e non accede ai loro salvataggi. L'immagine acquisita sara quella del nostro homebrew, letta dalla VRAM del GBA; non e ancora una cattura del gioco commerciale. In questa fase Fotocamera non viene usata.

**1. Carica Celio sul Pico**

1. Chiudi Fotocamera, PassoTile e qualsiasi programma che usa l'adattatore.
2. Spegni il GBA, rimuovi la cartuccia e scollega il Link dall'adattatore.
3. Scollega l'USB del Pico. Ricollegala tenendo premuto BOOTSEL, poi rilascia il pulsante.
4. Copia sul disco RPI-RP2 [RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2](dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2). Attendi che il disco scompaia.

Questo sostituisce temporaneamente il firmware webcam. Il file e la copia verificata del celio.uf2 fornito dal tuo amico, non un backup letto dal Pico. Il PC aveva gia riconosciuto questo tipo di dispositivo come GBLink USB con driver WinUSB: normalmente non occorre intervenire sui driver.

**2. Collega e avvia**

1. Con il GBA ancora spento e lo slot vuoto, collega il tuo abituale cavo Link fra adattatore e GBA SP, usando gli stessi connettori con cui funzionava PassoTile. Lascia il Pico collegato via USB.
2. Accendi il GBA SP senza cartuccia. Lascialo sulla schermata di avvio, in attesa del multiboot.
3. Fai doppio clic su [1-AVVIA-LINK-TEST.bat](1-AVVIA-LINK-TEST.bat).
4. Il programma trasferisce [gbmirroring-link-test-v0.2.0.gba](dist/gbmirroring-link-test-v0.2.0.gba). Sul GBA devono comparire **GBMIRRORING LINK TEST**, barre colorate e **NO CARTRIDGE REQUIRED**.
5. Lo script riavvia il solo Pico per riaprire il canale USB, poi esegue le misure. **Lascia acceso il GBA e non inserire cartucce.** Puoi premere A e B durante le misure: il rapporto registra i tasti ricevuti.
6. Se almeno una velocita risulta pulita, lo script acquisisce l'intera schermata. Durante la cattura l'indicatore sul GBA resta fermo: serve a mantenere coerenti tutti i pixel.

Prevedi alcuni minuti. La finestra mostra regolarmente i progressi; la cattura ha un limite massimo di 6 minuti. Non devi cambiare firmware o cavo a meta procedura.

Il software forza il percorso **GP3** della tua scheda. Nei moduli del tuo amico questa scelta si chiama `cable="gba"`: vale anche quando il cavo fisico utilizzato e GBC. Non selezionare automaticamente il percorso GP4 solo in base al nome del cavo.

**3. Leggi e inviami il risultato**

Ogni esecuzione crea una nuova cartella in [dist/link-reports](dist/link-reports), senza sovrascrivere le precedenti:

- **rapporto.json**: velocita effettive, pacchetti mancanti o duplicati, errori CRC, risposte ai comandi del PC e tasti ricevuti.
- **console.txt**: registro completo, inclusi eventuali errori di multiboot o USB.
- **schermo-gba.bmp**: compare soltanto se sono arrivati tutti i 600 blocchi verificati. Aprilo con un doppio clic e confrontalo con lo schermo del GBA. La piccola barra LINK ACTIVITY puo aver ripreso a muoversi sul GBA dopo la cattura.

Inviami rapporto.json e, se presente, schermo-gba.bmp. Se qualcosa si interrompe, aggiungi console.txt e dimmi cosa compare sul GBA.

| Esito | Significato |
|---|---|
| PASS | Tutte le velocita previste hanno superato il test e la cattura completa e riuscita. Non significa compatibilita con le cartucce. |
| PARTIAL | Esiste almeno una velocita pulita, ma una prova successiva o la cattura non e riuscita. I dati sono comunque utili. |
| FAIL | Nessuna velocita ha superato i criteri. Controlliamo rapporto e collegamento. |
| ERROR | Avvio, USB o esecuzione interrotti; il motivo e nel registro. |

Le velocita sono misure dell'intero percorso **GBA → Celio → USB → Python**, in byte di payload verificato al secondo. Non sono il baud rate elettrico, il limite massimo del Link o gli FPS ottenibili in un gioco. Questa prima prova resta in modalita multiplayer a 16 bit, con pause fra trasferimenti.

**Se qualcosa non parte**

- **Nessun device Celio / firmware diverso:** verifica di avere copiato l'UF2 Celio, non quello webcam. Puoi usare CONTROLLA-USB.bat per leggere lo stato USB.
- **Il GBA resta sul logo e il multiboot fallisce:** spegni il GBA, controlla Link e slot vuoto, riaccendilo e rilancia 1-AVVIA-LINK-TEST.bat. Conserva il registro se fallisce ancora.
- **Il nostro homebrew e gia visibile, ma il riavvio USB o la misura fallisce:** lascia acceso il GBA, chiudi la finestra del test, scollega e ricollega soltanto l'USB del Pico senza BOOTSEL, poi lancia [2-MISURA-LINK.bat](2-MISURA-LINK.bat). Questo secondo file salta il multiboot; non usarlo se sul GBA c'e ancora il logo iniziale o un gioco.
- **Screenshot incompleto:** non viene salvata un'immagine apparentemente valida con pixel mancanti. Inviami il rapporto; non cambiare driver a tentativi.

Al termine puoi spegnere il GBA. Per tornare alla prova webcam, scollega il Link e carica con BOOTSEL [gbmirroring-uvc-test-v0.1.0.uf2](dist/gbmirroring-uvc-test-v0.1.0.uf2).

**Verifiche gia eseguite**

Il programma ARM e compilato con controlli degli avvisi attivi. Header, punti di ingresso e dimensione del multiboot sono verificati. Sette test automatici controllano errori del protocollo, invio multiboot simulato e l'esecuzione del binario ARM con registri GBA simulati: la cattura prodotta contiene tutti i pixel attesi. Il [rapporto software](dist/verifica-link-software.json) distingue questi controlli dal test fisico, che deve ancora essere eseguito.
