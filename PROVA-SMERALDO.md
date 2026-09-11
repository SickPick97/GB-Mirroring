# Smeraldo italiano - pacchetto sperimentale 0.5.1

Contiene un loader multiboot per la cartuccia italiana originale, un payload residente e un visualizzatore PC. Il Pico mantiene il firmware SD 0.4.0. Non servono ROM sul PC, Python installato, emulatori aperti o connessioni Internet durante la prova. Il renderer mGBA e gia incluso e riceve solo lo stato grafico; non esegue Smeraldo sul PC.

## Cosa e verificato

La 0.5.0 ha funzionato sulla cartuccia dell utente, ma con rallentamento e blocchi neri. Questa versione distribuisce l invio tra piu fotogrammi e recupera l allineamento a bit sul PC. Il limite e un blocco inviato per interrupt, invece di una schermata intera. Verifiche ARM e protocollo superate; le nuove prestazioni hardware sono da misurare.

Aspettati una prima immagine dopo circa 7-15 secondi, e streaming piu lento. La priorita di questa prova e la velocita del gioco sul GBA. I blocchi vengono letti in momenti diversi: durante movimento e transizioni l anteprima puo mostrare temporaneamente parti non coerenti.

Limiti attuali: effetti per scanline non riprodotti, nessuna webcam UVC, possibili pause al primo invio, ai cambi scena e ai reinvii completi periodici. Non e certificata l intera partita, incluse tutte le battaglie o il salvataggio con payload attivo. Non usare il Cable Club durante questa prova: la porta Link e occupata dalla cattura.

## Procedura

1. Scarica/estrai la versione 0.5.1 in una cartella nuova; avvia 0-CONTROLLA-PC.bat. Chiudi Fotocamera, PassoTile e gli altri test.
2. GBA spento, cartuccia rimossa. Ripristina il Pico con dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2 mediante BOOTSEL.
3. Mantieni il cavo come sempre: piccolo nell adattatore, grande nel GBA, selettore GBA, presa centrale vuota. Accendi il GBA senza cartuccia.
4. Avvia 12-CARICA-SMERALDO.bat. Attendi sul GBA INSERT CART THEN START. Chiudi il BAT quando il multiboot e completato.
5. Lascia acceso il GBA, inserisci Smeraldo italiano originale, poi premi START. Questo e l inserimento a caldo previsto dal loader, come nel progetto precedente. Se compare WRONG CART OR REVISION, fermati e riferisci il messaggio: non tentare altre cartucce. Il codice non forza l avvio di un profilo diverso.
6. Quando Smeraldo e partito, lascia acceso il GBA e cambia soltanto il firmware Pico: scollega USB, ricollega con BOOTSEL, copia dist/gbmirroring-sd-video-v0.4.0.uf2 su RPI-RP2. Non attivare ancora la cattura.
7. Carica la partita e portati all aperto. Avvia 13-VIDEO-SMERALDO.bat della nuova cartella. Attendi PRONTO nella console.
8. Premi insieme SELECT + L + R e rilasciali: abilita la trasmissione. La pagina si apre su http://127.0.0.1:8765 . Attendi fino a 15 secondi per la prima immagine. Gli FPS richiedono 5 secondi per stabilizzarsi.
9. Resta fermo 20 secondi, cammina per 30 secondi, entra/esci da un Centro Pokemon e apri/chiudi la squadra. Dopo ogni transizione attendi 15 secondi senza riavviare il viewer. Metti anche in pausa la cattura con SELECT+L+R per confrontare la velocita del gioco, poi riattivala e attendi il reinvio. Confronta GBA e anteprima: testo, posizione, colori e velocita della partita. In questa prima prova fermati prima di fare nuove modifiche alla partita che vorresti salvare.
10. Premi SELECT + L + R per mettere in pausa la cattura, poi Termina e salva rapporto nella pagina. Spegni il GBA prima di rimettere Celio o rimuovere la cartuccia. Il payload scompare spegnendo; non modifica la ROM della cartuccia.

## Se qualcosa non funziona

- Schermo GBA nero o gioco bloccato dopo START: spegni e invia il log multiboot e il messaggio/fase osservati.
- Nessuna immagine: verifica PRONTO e la combinazione SELECT + L + R; attendi 15 secondi. Se resta vuoto, termina e invia il rapporto. Non invertire il cavo e non cambiare driver.
- Dopo una perdita il decoder attende un reinvio completo. Pausa e riattiva con SELECT + L + R (rilasciando fra le due pressioni) per richiederlo dal GBA. Il reinvio richiede diversi secondi.
- Se chiudi e riapri il viewer, metti prima in pausa il GBA, poi attendi il nuovo PRONTO e riattiva la cattura.
- Dopo spegnimento o soft reset occorre rifare il multiboot. Chiudere solo la scheda browser non termina il processo.

## Risultati da inviare

Nella nuova cartella dist/emerald-reports/<data-ora>: rapporto.json, frames.jsonl, ultimo-frame.bmp se presente e usb-tail.bin. In caso di problema iniziale aggiungi console.txt dalla sottocartella boot-<data-ora>. Indica anche se il gioco sul GBA rallenta o se noti differenze rispetto alla pagina. Non serve inviare ROM o salvataggi.

Il campo has_verified_frames indica frame ricostruiti da pacchetti validati, non una certificazione automatica della fedelta di ogni effetto grafico. raster_dma_active segnala un possibile effetto DMA per scanline non supportato. Gli FPS del PC contano immagini ricevute, non latenza totale.
