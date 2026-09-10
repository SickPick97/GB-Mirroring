# Prova multiplayer estesa - pacchetto 0.3.4

Scopo: misurare il margine riducendo le pause del trasporto gia funzionante. Non e ancora un nuovo trasporto video o una webcam GBA. I firmware Celio e GBA 0.2.0 sono invariati.

1. Chiudi Fotocamera, PassoTile e vecchie finestre di misura. Spegni il GBA e togli la cartuccia.
2. Ripristina sul Pico con BOOTSEL il file dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2. Attendi la scomparsa di RPI-RP2.
3. Mantieni il cavo GBA: spinotto piccolo nell'adattatore, grande nel GBA, presa centrale vuota, selettore GBA. Non invertirlo durante la prova.
4. Accendi il GBA senza cartuccia. Avvia 5-AVVIA-LINK-ESTESO.bat. Il multiboot e il riavvio del solo Pico sono automatici. Lascia acceso il GBA.
5. Aspetta circa 5 minuti, eventualmente di piu per la schermata. Puoi premere A/B: non servono per avviare le fasi.
6. Invia rapporto.json, console.txt e schermo-gba.bmp (se prodotto) dalla nuova cartella dist/link-reports.

La scansione prova timing 1000, 500, 250, 125, 60, 30, 10, 1, per 20 secondi ciascuno. Sono parametri di pausa PIO, non frequenze o FPS. Al primo errore si ferma la scansione. Poi riprova per 60 secondi il miglior timing pulito e tenta una schermata a un livello piu conservativo. Se una fase fallisce, PARTIAL e un risultato utile: non significa che tutto il test sia inutilizzabile. La conferma puo fallire se il collegamento non recupera dopo una fase troppo veloce; il rapporto lo conserva.

Se il multiboot riesce ma la riapertura USB fallisce, lascia acceso il GBA con GBMIRRORING LINK TEST visibile, chiudi il programma, scollega e ricollega solo USB senza BOOTSEL e avvia 6-RIPRENDI-LINK-ESTESO.bat. Non usarlo sulla schermata iniziale Nintendo.

Se Celio non viene trovato, usa CONTROLLA-USB.bat e invia il risultato. Non installare altri driver a tentativi.

Il confronto con 2623,9 B/s del vecchio test comprende anche USB e PC: non isola il cavo. Una curva che smette di crescere suggerira di intervenire sui costi fissi del trasporto; errori crescenti indicheranno il limite di questa configurazione da indagare. Nessun miglioramento e ancora confermato su hardware.

La prova Normal con cavo invertito dopo il multiboot resta una possibile diagnosi alternativa, concordata se necessaria. Il prodotto finale deve funzionare senza invertire il cavo.
