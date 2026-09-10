# Video SD 0.4.0 - nuova strada, cavo fisso

Obiettivo del banco: video 240x160 del nostro homebrew, 5-10 FPS quando dati e tempo CPU lo consentono. Non sono prestazioni ancora dimostrate sul dispositivo e non e cattura da Smeraldo/Verde Foglia. Usa un protocollo software sincrono su SC e SD tramite RCNT GPIO; Pico passivo PIO/DMA, USB CDC standard, visualizzatore locale sul PC. Nessuna modifica hardware e nessuna inversione del cavo.

## Avvio

1. Estrai il pacchetto 0.4.0 in una cartella nuova e avvia 0-CONTROLLA-PC.bat. Chiudi Fotocamera, PassoTile e i vecchi test.
2. Spegni il GBA, slot vuoto. Ripristina sul Pico dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2 con BOOTSEL: il firmware 0.3.7 non effettua il multiboot.
3. Mantieni piccolo nell'adattatore, grande nel GBA, presa centrale vuota e selettore GBA. Accendi il GBA senza cartuccia.
4. Avvia 10-CARICA-VIDEO-SD.bat. Aspetta multiboot completato e LOAD SD VIDEO UF2 sul GBA. Chiudi il BAT. NON premere ancora A.
5. Lascia acceso il GBA. Scollega solo USB; ricollega il Pico tenendo BOOTSEL e copia dist/gbmirroring-sd-video-v0.4.0.uf2 su RPI-RP2.
6. Avvia 11-VIDEO-SD.bat dalla nuova cartella. Si apre una pagina locale. Se non si apre, visita http://127.0.0.1:8765 . Attendi PRONTO nella console, poi premi e rilascia A sul GBA.
7. Dovresti vedere lo schermo animato del GBA nella pagina. La prima finestra di calcolo FPS richiede 5 secondi. Il contatore unique_fps_last_5s conta frame nuovi validati, non ridisegni della pagina. Il sender punta a un massimo di circa 10 FPS; se impiega piu tempo il ritmo scende automaticamente.

## Prova guidata (circa due minuti)

- Lascia la scena 0 per 30 secondi: barre e oggetto in movimento, immagine facilmente comprimibile.
- Premi e rilascia B, attendi 30 secondi: scena 1 a scorrimento, molte variazioni.
- Premi e rilascia B, attendi 20 secondi: scena 2 pseudo-casuale poco comprimibile. Il calo FPS e previsto e quantifica il limite del trasporto; non deve essere confuso con gli FPS delle scene facili.
- In RAW i frame possono durare piu a lungo: tieni premuti i tasti circa un secondo perche il programma li legge fra i frame.
- Premi B per tornare alla scena 0, poi A: modalita RAW senza compressione, attendi 20 secondi. Premi A di nuovo per riattivare RLE.
- Se non arrivano immagini o aumentano i CRC, premi e rilascia L per la modalita SLOW e attendi 10 secondi. Questa allunga gli impulsi senza cambiare il cavo. Riporta se hai usato L. Non installare driver a tentativi.
- Premi Termina e salva rapporto nella pagina. Poi spegni il GBA. Non caricare Celio mentre il sender GPIO e ancora in esecuzione sul GBA.

Se non vedi immagini dopo circa 30 s, termina comunque e invia i risultati. In caso di errore READY/COM o overrun, conserva il messaggio e il rapporto. Per ripetere da uno stato noto, spegni il GBA e riparti dal punto 2. Chiudere soltanto la scheda browser non termina la cattura: usa il pulsante oppure Ctrl+C nella console.

## File da inviare

Nuova cartella dist/sd-video-reports: rapporto.json, frames.jsonl e ultimo-frame.bmp (se almeno un frame ha superato il CRC). Il rapporto viene salvato anche periodicamente. I tempi del registro sono misure lato PC; non equivalgono a latenza LCD->monitor. Se chiudi bruscamente il processo, l'ultimo BMP potrebbe non essere salvato.

## Cosa e incluso

Programma GBA 0.4.0 compilato (codice e codec in IWRAM, buffer in EWRAM), Pico UF2 0.4.0, decoder RLE16 con keyframe autonomi, app browser offline. Non e ancora una webcam UVC; il requisito finale rimane UVC autonomo. Non occorrono Python installato, librerie nuove o Internet durante la prova. Il software su PC usa solo il driver CDC di Windows.

Ogni fotogramma contiene tutti i pixel letti dalla VRAM. Non si inviano coordinate di oggetti da ridisegnare con asset sul PC. CRC32 dei pixel e CRC16 dell'header; i frame errati non vengono visualizzati. Ogni frame e indipendente: una perdita non contamina le immagini successive, ma una perdita di sincronismo a livello di bit puo richiedere il riavvio della prova. RLE ripiega su RAW se non riduce i dati. Non e una garanzia di 5-10 FPS per immagini arbitrarie o giochi commerciali.
