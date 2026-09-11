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

2026-09-10, secondo riscontro: firmware 0.3.3 e data_pin=3 confermati dal ready. Rapporto e log coerenti: 290664 parole, zero header, campioni registrati tutti nulli, nessuno stall PIO segnalato. Il cambio GP1 -> GP3 non ha risolto. Non ancora verificato orientamento del cavo o percorso del segnale GBA -> adattatore. Nessuna nuova versione firmware consegnata in attesa di chiarire il cablaggio. Evidenza ripulita: test-results/2026-09-10-normal-v0.3.3/summary.json.

2026-09-10, multiplayer esteso pacchetto 0.3.4: PASS hardware a cavo fisso. Otto finestre da 20 s pulite: timing 1000=1868,5; 500=2617,2; 250=3276,6; 125/60/30/10=3449,6; 1=3448,4 B/s. Conferma timing 125 per 60,006 s: 3451,4 B/s, 1619 pacchetti, zero CRC/pattern/mancanti/duplicati/errori seriali incrementali. Tasti non verificati (mask 0). Screenshot timing 250: 600 blocchi, zero CRC, 23,45 s; SHA256 verificato e immagine 240x160 ispezionata. Multiboot 3,676 s, zero desync, un riavvio riportato.

Guadagno circa 31,5% rispetto al massimo precedente; screenshot da 41,08 a 23,45 s. Plateau da timing 125: nessuna prova che sia il limite elettrico del Link. Restano da separare costi GBA/Pico/USB. A 3451,4 B/s un frame grezzo 76800 byte richiederebbe almeno 22,25 s, senza costi aggiuntivi: non ancora video fluido. Evidenza ripulita in test-results/2026-09-10-link-extended-v0.3.4. Cavo confermato piccolo lato adattatore, grande lato GBA, selettore GBA; nessuna inversione. Normal con inversione mantenuto solo come alternativa diagnostica.

Profilo 0.3.5, 2026-09-10: PASS. Timing 500=2619,6 B/s; due finestre timing 125=3451,2 e 3451,3 B/s. Delta contatori GBA 44208/58248/58248, esattamente quelli attesi. Nessun errore. USB a timing 125: 116562 byte e 2912 letture per finestra, soprattutto blocchi da 40 byte; lettura media 10,17 ms inclusa attesa. Coda massima campionata 20 parole, CPU processo 0,5-0,5312 s per 30 s: non emerge un arretrato significativo nel parser. Velocita USB 3884,9 B/s comprende overhead del protocollo (72 parole totali per 64 di payload). Screenshot timing 125 completo, 22,26 s, hash e immagine verificati.

I sorgenti di riferimento del relay includono sleep 10 ms, coerente con la cadenza; tuttavia il sorgente disponibile invia blocchi fissi da 64 byte mentre il binario osservato produce soprattutto 40 byte. Non e provata la corrispondenza esatta sorgente/binario. Non attribuire ancora il plateau alla pausa USB: resta da misurare la produzione sul Pico indipendentemente dalla consegna USB. Evidenza ripulita in test-results/2026-09-10-link-profile-v0.3.5.

Pico Multi Profile 0.3.6, 2026-09-10: PASS hardware sullo stesso cavo fisso. Due finestre da 30 s: timing 1000, 31490 parole, 437 pacchetti, 1866,1 B/s; timing 125, 62765 parole, 871 pacchetti, 3719,4 B/s. CRC, pattern, sequenze, errori seriali incrementali e pio_fdebug tutti zero. Rapporto coerente con usb.jsonl e velocita ricalcolate. Nessuna immagine prevista. Evidenza selezionata in test-results/2026-09-10-pico-profile-v0.3.6.

A timing 125 +7,77% rispetto a Celio/PC 3451,3 B/s; confronto fra implementazioni diverse, non isolamento del solo costo USB. Il nuovo firmware e ora una base multiplayer verificata. Timing 125 mantiene ancora una pausa: prima di dichiarare un plateau della nuova implementazione serve una scansione locale con pause inferiori. I circa 20,65 s teorici per un frame grezzo non sono una misura di cattura/streaming.

Pico scan 0.3.7, 2026-09-10: PASS hardware. Timing 125/60/30/10/1: 3719,4 / 4015,7 / 4169,0 / 4277,8 / 4328,7 B/s, ciascuno su 20 s. Conferma timing 1 su 60,000002 s: 146093 parole, 2028 pacchetti, 4328,7 B/s; CRC/pattern/sequenze/errori seriali incrementali e pio_fdebug tutti zero. Rapporto confrontato con usb.jsonl; numeratori e velocita ricalcolati. Evidenza selezionata in test-results/2026-09-10-pico-scan-v0.3.7.

Guadagno +16,38% rispetto alla precedente misura locale a timing 125; da timing 10 a 1 solo +1,19%. Margine della pausa quasi esaurito, non dimostrato limite fisico del cavo. Frame grezzo 76800 byte: stima minima 17,74 s al payload misurato. Nessuna nuova prova di screenshot, streaming USB/UVC o cartucce in questa versione. Prossimo lavoro: valutare costi fissi del protocollo e trasferimento di immagini sul nuovo firmware, evitando altre scansioni minime della stessa pausa.

Nuova direzione 0.4.0: sender GPIO SC/SD e codec in IWRAM, ricezione passiva PIO/DMA e viewer PC. Solo verifiche software al momento: nessuna banda o FPS reali dichiarati. Target utente 5-10 FPS, senza modifiche hardware e con cavo fisso. Richiede nuovo multiboot GBA e firmware Pico; i risultati precedenti multiplayer restano validi come confronto.

2026-09-10, SD video 0.4.0: ricezione hardware riuscita, obiettivo FPS ancora non raggiunto. 332 frame consecutivi (0..331), 14454946 byte, zero CRC/header/scarti/gap/duplicati. Somma frame verificata contro rapporto. Fase RAW 0..111: 1,3307 FPS e 102229 B/s fra arrivi; RLE 112..113: solo due frame, non misura sostenuta; RLE 114..272: 3,5544 FPS su 44,4524 s; RLE 273..331: 1,4004 FPS. Ultimo BMP 240x160 ispezionato: SCENE 2, L FAST. Velocita include rendering, codec e trasporto, non sola banda elettrica. Stato finale STREAMING nel rapporto; non prova arresto pulito. Log non identifica scene/timing per ogni frame, ne motivo RAW iniziale. Evidenza selezionata in test-results/2026-09-10-sd-video-v0.4.0. Prossimo sviluppo: profilare costi GBA e ottimizzare sender/codec; registrare scene e timing espliciti.

0.4.1: nuovo programma GBA e decoder testati in software; firmware Pico 0.4.0 invariato. Nessun risultato hardware FPS ancora disponibile. Utente conferma Smeraldo italiano originale, candidato profilo BPEI del loader analizzato. Non ancora cattura dalla cartuccia.

2026-09-11, SD video 0.4.1: 732 frame consecutivi 0..731, 8534304 byte, zero CRC/header/gap/duplicati/riferimenti delta mancanti/scarti. BMP ispezionato SCENE 0 L FAST. Scene FAST 0/1/2: 4,053 / 3,008 / 1,927 FPS nelle prime tre fasi; scena 0 BASE 3,992 FPS, successiva FAST 4,054. Prima scena 0: rendering 51,68 ms, copia 32,04 ms, CRC 66,38 ms, codec/riferimento 91,96 ms, TX 4,33 ms in media. TX attribuito al frame tramite previous_tx del successivo; campione finale escluso. Elaborazione domina scena 0, mentre scena 2 TX medio 255,80 ms resta rilevante. Nessuna prova RAW in questa sessione. Obiettivo FPS non raggiunto; prossima ottimizzazione CPU/copie/codec, non solo clock. Evidenza selezionata test-results/2026-09-11-sd-video-v0.4.1.


0.5.0: implementato il primo loader residente per Smeraldo italiano e renderer PC. Solo verifiche software: 90/90 immagini identiche nella sequenza mGBA; 9,46 catture/s in campo statico emulato, 56,74 VBlank gioco/s. Nessun nuovo risultato hardware. Evidenza ripulita in test-results/software-v0.5.0/summary.json. Procedura PROVA-SMERALDO.md; UVC e scanline ancora aperti.


2026-09-11, Smeraldo 0.5.0: utente conferma immagini dalla cartuccia originale sul PC, menu e overworld visibili, ma forte rallentamento del GBA. Due sessioni: 278 e 239 frame validi; negli intervalli fra primo e ultimo frame 8,405 e 8,607 FPS. Contatore VBlank del gioco circa 50,43 e 51,64/s, non misura diretta dei frame di gameplay. Entrambi gli ultimi BMP sono completamente neri. Il primo termina a sequenza 277, il secondo a 958; byte ricevuti continuano oltre gli ultimi frame e vengono scartati, CRC e header registrati zero. Seconda prova 39 riferimenti delta mancanti. Riavvio viewer ripristina il video secondo l utente. Ipotesi di disallineamento dei bit durante reinizializzazione Link, non provabile senza raw USB. Evidenza ripulita in test-results/2026-09-11-emerald-v0.5.0.

0.5.1: scheduler suddiviso e parser riallineabile preparati. Solo collaudo software; nessuna nuova fluidita hardware dichiarata.


2026-09-11, Smeraldo 0.5.1: collaudo utente positivo per fluidita GBA e recupero delle transizioni Centro Pokemon/menu. 261 frame 0..260, zero CRC/header/gap/duplicati/riferimenti mancanti, cinque riagganci riportati e 104 byte scartati; arresto pulito. FPS fra primo/ultimo frame 1,537 su 169,135 s; mediana intervallo 0,586 s, massimo 7,049 s. Media non-keyframe 20,83 blocchi / 5895 byte; keyframe 0,49,75,159. Ultimo BMP ispezionato con scena di gioco visibile, non confronto pixel per pixel. Conteggi e lunghezze ricalcolati da frames.jsonl. Evidenza selezionata test-results/2026-09-11-emerald-v0.5.1; log grezzi e coda USB non pubblicati. Target 10 FPS ancora aperto. Piano PIANO-STREAMING-FIRMWARE-UNICO.md; nessuna modifica software in questo aggiornamento.
