# Misura locale sul Pico - 0.3.6

Questa prova usa un NUOVO firmware multiplayer Pico e il programma GBA Link 0.2.0 gia collaudato. Non e una versione verificata su hardware; serve a confrontare la nuova implementazione con Celio. Mantiene il cavo fisso. Non produce schermate e non usa cartucce.

1. Estrai il pacchetto e avvia 0-CONTROLLA-PC.bat. Chiudi Fotocamera, PassoTile e ogni test USB precedente.
2. Sul Pico deve esserci Celio. Se necessario, a GBA spento ripristina dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2 con BOOTSEL.
3. Cavo: piccolo nell'adattatore, grande nel GBA; selettore GBA; presa centrale vuota. Accendi il GBA senza cartuccia.
4. Avvia 8-CARICA-PROFILO-PICO.bat. Aspetta multiboot completato e GBMIRRORING LINK TEST sul GBA. Chiudi il BAT.
5. LASCIA ACCESO IL GBA. Scollega solo USB, ricollega il Pico tenendo BOOTSEL e copia dist/gbmirroring-multi-profile-v0.3.6.uf2 su RPI-RP2. Non invertire il cavo.
6. Avvia 9-MISURA-PICO.bat. Non premere tasti. Il Pico resta passivo finche il PC invia START, poi esegue timing 1000 e 125, fino a 30 secondi ciascuno. Sul PC appare un messaggio di attesa ogni 5 secondi e un risultato a fine fase. Se la prima fase fallisce la seconda non parte.
7. Invia rapporto.json e usb.jsonl dalla nuova cartella dist/pico-reports. Poi puoi spegnere il GBA.

Il programma verifica CRC, pattern, sequenze, risposte alla challenge ed errori seriali del GBA direttamente sul Pico. Calcola il tempo fra primo e ultimo pacchetto valido, escludendo il primo dal numeratore. Conta separatamente tutte le parole e la durata della finestra. Non trasmette il flusso dati su USB durante la misura, ma continua a gestire USB e controlla che il PC sia connesso. Questi tempi includono il nuovo codice di controllo/validazione, non soltanto il filo.

Non e una misura interna del vecchio firmware Celio: il confronto include il cambio di implementazione. Il campo pio_fdebug conserva le indicazioni FIFO hardware; non e una misura completa delle attese della macchina PIO. Un fallimento qui non invalida il precedente test Celio.

Se il GBA si spegne durante il cambio firmware, riparti dal punto 2. Per ripetere da uno stato noto riparti dal punto 2. Per tornare a PassoTile o ai test precedenti ripristina Celio a GBA spento. La futura integrazione del multiboot eliminera questo cambio manuale; l'inversione del cavo resta solo un'alternativa diagnostica, non parte di questa prova.
