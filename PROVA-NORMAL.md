**Terza prova: Link seriale normale a 256 kHz e 2 MHz**

Il banco precedente ha trasferito correttamente una schermata dal GBA e misurato 2623,9 B/s attraverso Celio. Ora usiamo un nuovo programma GBA e un nuovo firmware Pico: il GBA genera il clock, il Pico riceve con PIO e DMA. Il firmware Pico controlla direttamente i dati e invia risultati e schermate al PC tramite una porta USB seriale standard.

Tutto e gia compilato. Non devi installare Python, librerie o driver aggiuntivi. La prova resta **senza cartuccia** e non usa Fotocamera. Non sono richieste modifiche hardware. Usa il cavo GBA e gli stessi connettori della prova riuscita, mantenendo la configurazione elettrica GBA dell'adattatore.

**Aggiornamento 0.3.2:** il ricevitore stampa una riga diagnostica ogni due secondi anche senza pacchetti validi. Il programma GBA resta V030. Se dopo A non compaiono pacchetti, non premere B: attendi il timeout (massimo tre minuti) e invia rapporto.json, host.json e usb.jsonl. Un conteggio parole maggiore di zero indica che il ricevitore ha campionato gruppi di 32 bit; non dimostra da solo dati corretti. Zero parole non identifica da solo un guasto del cavo.

**Passo 1: multiboot con Celio**

1. Chiudi Fotocamera, PassoTile e le finestre dei test precedenti.
2. Sul Pico deve esserci **Celio**, come nell'ultima prova riuscita. Se hai caricato un altro firmware, ripristina con BOOTSEL [RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2](dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2) prima di continuare.
3. Spegni il GBA SP e togli la cartuccia. Collega il tuo cavo Link e lascia il Pico collegato via USB.
4. Accendi il GBA con slot vuoto. Avvia [3-CARICA-NORMAL.bat](3-CARICA-NORMAL.bat).
5. Sul GBA deve comparire **GBMIRRORING NORMAL V030**, con la richiesta di caricare il firmware Pico. Aspetta che il BAT annunci il multiboot completato, poi chiudi quella finestra.

**Lascia acceso il GBA e NON premere A.** Il programma resta nella sua RAM mentre cambi il firmware del Pico.

**Passo 2: cambia soltanto il firmware Pico**

1. Lasciando acceso il GBA, scollega soltanto l'USB del Pico dal PC. Puoi lasciare il cavo Link collegato.
2. Ricollega l'USB tenendo premuto BOOTSEL, poi rilascia il pulsante.
3. Copia su RPI-RP2 [gbmirroring-normal-test-v0.3.2.uf2](dist/gbmirroring-normal-test-v0.3.2.uf2).
4. Attendi che RPI-RP2 scompaia e che Windows riconosca la porta USB. Il dispositivo si chiama **GBMirroring Normal Test**, oppure appare come dispositivo seriale USB con una porta COM.

Il nuovo firmware tiene tutti i pin Link in ingresso e ascolta SC su GP0 e dati su GP1. Durante questa attesa anche il programma GBA lascia le linee in ingresso. **Non premere A prima che il prossimo script dica PRONTO**: il GBA deve generare il clock solo quando Celio e stato sostituito dal ricevitore.

**Passo 3: misura e cattura**

1. Avvia [4-MISURA-NORMAL.bat](4-MISURA-NORMAL.bat).
2. Quando il PC mostra **PRONTO**, premi e rilascia **A sul GBA**. Parte la prova a 256 kHz.
3. Il GBA invia 1 MiB di dati con pattern verificabile, poi una schermata completa. Sul PC avanzera il conteggio fino a 1024 pacchetti. Il testo GBA resta fermo durante ciascuna misura: e previsto.
4. Aspetta che il PC confermi il completamento e chieda di proseguire. Solo allora premi e rilascia **B sul GBA** per la prova a 2 MHz.
5. Aspetta l'esito finale. Puoi quindi spegnere il GBA.

Prevedi alcuni minuti. Le scritte 256 kHz e 2 MHz indicano le modalita del GBA; nel rapporto i clock nominali sono 262144 e 2097152 Hz. La porta COM viene aperta a 115200, ma essendo USB CDC quel numero non limita la velocita del Link o del trasferimento USB.

La prova a 2 MHz serve proprio a capire se il tuo cavo e il convertitore di livelli mantengono integri i dati a quella velocita: non e garantito che passi. Se 256 kHz fallisce, il PC interrompe la procedura e non chiede di avviare la fase veloce.

**Risultati da inviarmi**

In [dist/normal-reports](dist/normal-reports) trovi una nuova cartella con:

- **rapporto.json**: esito, velocita utile GBA → Pico, contatori di errori e integrita delle schermate.
- **schermo-262144.bmp** e **schermo-2097152.bmp**: immagini ricevute dalla VRAM del GBA, salvate solo quando complete e con CRC32 corrispondente fra Pico e PC.
- **host.json** e **usb.jsonl**: stato del programma Windows e registro del firmware, utili in caso di problemi.

Inviami rapporto.json e le due immagini. Se qualcosa fallisce, manda anche host.json e usb.jsonl. Il registro del multiboot e in una cartella distinta con prefisso **boot-**.

La velocita principale e misurata **sul tratto GBA → Pico**, con validazione sul Pico. Il banco precedente includeva anche USB e Python: il confronto non isola il solo aumento del clock. Il passaggio della schermata al PC e verificato separatamente. La prova non dimostra ancora streaming webcam, cattura dalle cartucce, comunicazione bidirezionale o stabilita di lunga durata.

**Se qualcosa non funziona**

| Situazione | Cosa fare |
|---|---|
| Il multiboot non parte | Verifica Celio sul Pico, GBA acceso con slot vuoto e cavo della prova precedente. Spegni/riaccendi il GBA e ripeti il passo 1. |
| Il GBA si spegne durante il cambio UF2 | Il programma RAM e perso: ripristina Celio e ricomincia dal passo 1. |
| Il PC non trova GBMirroring Normal Test | Attendi alcuni secondi e rilancia 4-MISURA-NORMAL.bat. Verifica di avere copiato l'UF2 normal, non quello UVC o Celio. Non usare Zadig. |
| Il PC e pronto ma non riceve dopo A | Inviami il rapporto: potrebbe mancare il percorso SO → SI sul cavo, oppure il clock non viene rilevato. Il successo in multiplayer non verifica queste linee in modalita normale. |
| Hai premuto A prima di PRONTO | Se Celio era gia stato sostituito, il Pico potrebbe essersi perso l'inizio. Attendi che il GBA arrivi alla richiesta B, premi B senza trarre conclusioni dalla prova, attendi DONE, poi usa START come descritto sotto. |
| 2 MHz produce errori | Conserva i dati. Non cambiare cablaggio o convertitore a tentativi: valutiamo prima quale fase ha fallito. |

Per ripetere con il nuovo firmware gia caricato: il GBA deve avere concluso entrambe le fasi e mostrare DONE. Chiudi lo script PC, premi START sul GBA per tornare alla schermata iniziale, riavvia 4-MISURA-NORMAL.bat, poi premi A quando compare PRONTO. Se non sei sicuro dello stato, spegni il GBA e riparti dal passo 1 con Celio.

Per tornare alla webcam sintetica, spegni il GBA, scollega il Link e carica [gbmirroring-uvc-test-v0.1.0.uf2](dist/gbmirroring-uvc-test-v0.1.0.uf2). Per tornare a PassoTile, ripristina l'UF2 Celio.

**Stato delle verifiche**

Compilati entrambi i binari. Verificati header multiboot, boot RP2040, UF2, descrittori CDC, allineamento DMA e buffer immagine. Nei test il codice ARM GBA esegue entrambe le fasi, con verifica indipendente di tutti i pacchetti e di entrambe le schermate. Testati inoltre il campionamento PIO su fronti ideali e il rifiuto di screenshot USB incompleti o corrotti. Il cablaggio fisico, i fronti elettrici, DMA e USB sul Pico reale restano da collaudare con questa procedura.
