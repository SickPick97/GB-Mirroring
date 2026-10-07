# Avvio e collaudo unico (programma GBA 0.13.0, pacchetto 0.15.2)

[English quick start](docs/QUICKSTART.en.md). Pacchetto pronto, senza compilazione. Il Pico unificato **0.7.0 resta compatibile**: non occorre riflasharlo.

Questa e la linea stabile 0.15.2: sul GBA gira il programma 0.13.0 (quello che andava bene) e sul Pico il firmware **0.7.0**. Se il Pico ha un firmware 0.8.x, riflashalo con `dist/gbmirroring-unified-v0.7.0.uf2` (BOOTSEL premuto mentre colleghi l USB, poi copia il file su `RPI-RP2`). I miglioramenti sono solo sul PC: pose di corsa corrette, dissolvenza dopo i caricamenti, riproduzione piu regolare. Il pulsante **Scarica log** crea un unico file da inviarmi. **Salvataggio:** il residente non legge ne scrive la memoria di salvataggio. Per sicurezza fai comunque una copia del tuo `.sav` prima della prova.

**Non c'e ancora una prova fisica di questa versione.** I numeri disponibili vengono da un gioco emulato, con il vero codice ARM del residente e un modello approssimato dei cicli: non misurano audio, tempi elettrici o presentazione del browser.

## Prima volta: copia della cartuccia

1. Estrai tutto lo pacchetto 0.15.2 in una nuova cartella scrivibile. Chiudi il vecchio BAT e la vecchia pagina.
2. Spegni il GBA, togli la cartuccia e riaccendilo. Apri **14-AVVIA-SMERALDO.bat** e premi **INVIO**. Non scegliere R.
3. Sul GBA inserisci Smeraldo italiano originale e premi **A** (non START). Compare una barra di avanzamento; il PC scrive la percentuale.
4. Quando il PC scrive `Cache ROM salvata`, chiudi il BAT. Il file e in `runtime/cache/` e non viene mai inserito nella repository. Spegni e riaccendi il GBA senza cartuccia.

Se la copia si interrompe o la ROM non viene riconosciuta, cancella `runtime/cache` e ripeti. Sono accettate solo cartucce italiane BPEI revisione 0.

## Avvio normale

1. Con il GBA acceso senza cartuccia, apri **14-AVVIA-SMERALDO.bat** e premi **INVIO** per caricare il residente 0.13.2. Mantieni cavo e selettore attuali.
2. Quando richiesto sul GBA, inserisci la cartuccia e premi **START**. Entra nella partita.
3. Quando il PC indica PRONTO, premi **SELECT + L + R** sul GBA. Il visualizzatore si apre su http://127.0.0.1:8765. La prima immagine arriva dopo alcuni secondi: il PC riceve prima la grafica iniziale.

## Una sola sessione

Parti da **Ceneride, fuori dal Centro Pokemon**. Prima di ogni tratto seleziona la fase nella diagnostica della pagina:

- fermo per dieci secondi;
- cammina per circa un minuto a destra e sinistra, poi in verticale; corri tenendo B;
- entra nel Centro Pokemon e cammina anche dentro;
- esci, apri e chiudi squadra, Pokedex e menu; prova una battaglia se disponibile;
- apri le informazioni di un Pokemon della squadra e scorri le pagine; affronta almeno due incontri in erba alta fino al comando LOTTA;
- salva la partita dal menu con lo streaming attivo (il test in emulazione scrive un salvataggio identico, salvo il tempo di gioco);
- controlla che gioco e audio sul GBA restino fluidi come senza streaming. SELECT + L + R mette in pausa e riprende la cattura per il confronto.

Alla fine premi **Scarica log** nella pagina: il browser scarica un unico file `log-<data-ora>.zip` (una copia resta in `dist/emerald-reports/<data-ora>`). Inviami quel solo file; non serve raccogliere cartelle. Puoi premerlo anche subito dopo un problema (per esempio dopo la battaglia), poi continuare. **Termina e salva rapporto** crea lo stesso zip in automatico. Il rapporto conta per ogni frame quanti blocchi e byte arrivano da mappe, palette, oggetti e copie dalla ROM, e quanti blocchi erano ancora in coda.

STREAM conta i tick ricevuti; NEL BROWSER conta le immagini presentate, senza contare il refresh della stessa immagine. IMMAGINI CAMBIATE esclude i frame visivamente identici. Le finestre sono di cinque secondi. Osserva anche a occhio: la fluidita percepita del movimento e il punto piu importante.

## Ripresa e OBS

R riprende il residente gia caricato nella stessa sessione della console. B carica la baseline 0.11.0 dopo spegnimento e riavvio senza cartuccia (non richiede la copia della cartuccia). Ripristina immagine richiede un riferimento completo mantenendo cavo e firmware.

Per OBS: sorgente Browser `http://127.0.0.1:8765/?clean=1`, dimensioni 240 x 160 o multipli. Il BAT deve restare aperto. Il buffer del browser e circa 200 ms.

## Cosa cambia e limiti

- **Un pacchetto per VBlank.** Se un VBlank non basta per tutti i blocchi cambiati, il residente segnala quanti restano; la pagina tiene i frame in ordine e li rilascia quando la cache e completa, ciascuno con il proprio stato. Il ritardo aggiuntivo in queste raffiche e di pochi VBlank, dentro il buffer da 200 ms.
- **Copie dalla ROM.** Il GBA emette il riferimento solo dopo aver confrontato la VRAM con la ROM parola per parola.
- **Tempo CPU.** Il residente lavora fino a circa 56 righe dopo il gestore VBlank del gioco. Nel test emulato il ciclo principale del gioco e stato controllato con lo stesso metodo delle versioni precedenti; l'audio resta da verificare sul GBA.
- Gli effetti per scanline restano incompleti. Un frame rilasciato dopo un ritardo usa la VRAM piu recente per i blocchi che erano in coda.
- Il pacchetto non contiene ROM o salvataggi e non richiede PROGETTO AMICO per funzionare.

Un futuro aggiornamento del Pico e consentito: il vincolo mantenuto e usare un solo firmware per multiboot e streaming durante tutta la procedura.
