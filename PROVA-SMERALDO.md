# Prova unica Smeraldo 0.8.0

Nuovo loader 0.8.0 e programma PC corretti; firmware Pico 0.7.0 invariato. Nessuna modifica al GBA o al cavo. In emulazione circa 18 catture/s; gli FPS reali e il nuovo feedback sul cavo devono essere verificati. La pagina web e ora l uscita definitiva richiesta.

## Preparazione, una sola volta per questo aggiornamento

1. Estrai tutto lo ZIP 0.8.0 in una cartella nuova e scrivibile. Chiudi i vecchi BAT/viewer.
2. Se hai gia il Pico 0.7.0 del test precedente, salta il flash. Solo per chi proviene da 0.6.0: con GBA spento, collega il Pico tenendo BOOTSEL. Copia **dist/gbmirroring-unified-v0.7.0.uf2** nell unita RPI-RP2. Attendi il riavvio. Questo flash serve per aggiornare da 0.6.0; non si ripete durante la sessione.
3. Conserva il cavo nella posizione attuale e il selettore GBA. Accendi il GBA senza cartuccia.

Per questo aggiornamento spegni il GBA ed esegui un nuovo multiboot con INVIO: R lascerebbe in memoria il vecchio residente.

## Avvio e prova

4. Apri **14-AVVIA-SMERALDO.bat** e premi INVIO. I file vengono controllati prima del multiboot.
5. Quando il GBA lo richiede, inserisci Smeraldo italiano originale e premi START. Non cambiare firmware e non scollegare USB.
6. Entra nella partita. Quando il programma dice PRONTO, premi e rilascia SELECT + L + R. Attendi fino a 15 secondi per la prima immagine.
7. Apri Diagnostica e fasi della prova, scegli la scena e premi Registra fase prima di provarla: fermo (30 s), cammino (almeno 60 s), menu/squadra, entrata e uscita Centro Pokemon, una battaglia, pausa e ripresa. Dedica circa 10 minuti alla sessione. Confronta anche il gioco con cattura attiva e in pausa tramite SELECT + L + R.
8. Se l immagine si ferma, attendi il recupero automatico. Il pulsante **Ripristina immagine** invia la stessa richiesta; se non riparte entro 15 s, registra il problema e usa pausa/ripresa sul GBA. Non invertire il cavo.
9. Metti in pausa la cattura, poi premi **Termina e salva rapporto**. Conserva l intera cartella **dist/emerald-reports/<data-ora>**. Comprende anche eventuali errore-*.bin, oltre a rapporto, frames, immagine e console. Invia tutta la cartella e indica fluidita GBA, eventuali artefatti e fasi problematiche.

## Ripresa e alternativa

- R nello stesso BAT riprende un residente gia caricato. Metti prima in pausa sul GBA, attendi PRONTO e riattiva la cattura. Dopo spegnimento serve invece INVIO e nuovo multiboot.
- Se la nuova cattura presenta problemi, puoi spegnere il GBA, togliere la cartuccia, riaccenderlo e scegliere **B**: carica il loader precedente 0.7.1 mantenendo lo stesso firmware Pico 0.7.0. Non richiede un altro UF2. Non e un passaggio obbligatorio del test.
- L errore WRONG CART OR REVISION ferma il loader: conserva il messaggio. Non sono supportate tutte le cartucce GBA.
- Il Pico usa CDC standard Windows. Non applicare driver Zadig.

## Uso con OBS

Il viewer offre la pagina senza controlli **http://127.0.0.1:8765/?clean=1**, per una sorgente Browser 240 x 160. Il programma GBMirroring deve restare aperto. Questa modalita e utile per acquisire l anteprima sul PC; non rende il Pico una webcam USB autonoma.

## Limiti e verifica

Confronta il valore STREAM in cammino con quello della precedente versione; IMMAGINI CAMBIATE esclude i frame visivamente identici. Questi contatori non misurano gli FPS del gioco sul GBA. La maggiore cadenza va collaudata anche per fluidita e audio della console.

Il percorso veloce osserva le code di copie nel callback overworld italiano verificato, con audit progressivo. Negli altri contesti mantiene la scansione completa: menu e battaglie possono avere FPS diversi. La cattura resta distribuita nel tempo e puo mostrare incoerenze transitorie; gli effetti scanline non sono implementati.

Le richieste di recupero usano uno slot half-duplex con rilascio della linea; la sua funzionalita elettrica e da collaudare. Se la risposta manca resta il refresh periodico. Il rapporto distingue feedback_available, richieste, errori CRC payload e altre invalidazioni. Il recupero invia ancora un frame completo e non garantisce meno di un secondo.

Test software: residente ARM, osservatore copie, protocollo, PIO, multiboot simulato, viewer HTTP e avvio portatile. I 90 confronti grafici esatti usano snapshot coerenti, non certificano tutta la cattura sul cavo. Il contatore VBlank non misura da solo gameplay o audio. Compatibilita dell intera partita e salvataggio con residente non certificati.
