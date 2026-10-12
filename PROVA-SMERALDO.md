# Avvio (programma GBA 0.16.0, pacchetto 0.16.0)

[English quick start](docs/QUICKSTART.en.md). Pacchetto pronto, senza compilazione.

**Pico: una volta sola, metti il firmware 0.8.1.** Tieni premuto BOOTSEL mentre colleghi l USB e copia `dist/gbmirroring-unified-v0.8.1.uf2` sull unita `RPI-RP2`. Serve perche il PC possa rispondere al GBA (blocchi annunciati, dissolvenze): il programma 0.16.0 e pensato per questo firmware. Se preferisci non toccare il Pico (0.7.0), all avvio scegli **S**.

All avvio: **INVIO** carica il programma nuovo 0.16.0; **S** carica quello stabile 0.13.0 (quello della linea 0.15.4), con lo stesso Pico e la stessa pagina. Se la 0.16.0 dovesse dare problemi, spegni il GBA, riavvia il BAT e scegli S: non serve cambiare cartella ne firmware.

**Questa versione non e stata provata sulla console.** E stata misurata con il residente vero dentro il gioco emulato (tempi del gioco compresi) e con il confronto immagine per immagine; cavo, Pico e browser non fanno parte di quelle prove. Il pulsante **Scarica log** crea un unico file da inviarmi. **Salvataggio:** il residente non legge ne scrive la memoria di salvataggio; il test in emulazione scrive un salvataggio identico. Per sicurezza tieni comunque una copia del tuo `.sav`.

## Prima volta: copia della cartuccia

1. Estrai tutto il pacchetto 0.16.0 in una nuova cartella scrivibile (la copia della cartuccia gia fatta si puo riusare: copia la cartella `runtime/cache` dal pacchetto precedente). Chiudi il vecchio BAT e la vecchia pagina.
2. Spegni il GBA, togli la cartuccia e riaccendilo. Apri **14-AVVIA-SMERALDO.bat** e premi **INVIO**. Non scegliere R.
3. Sul GBA inserisci Smeraldo italiano originale e premi **A** (non START). Compare una barra di avanzamento; il PC scrive la percentuale.
4. Quando il PC scrive `Cache ROM salvata`, chiudi il BAT. Il file e in `runtime/cache/` e non viene mai inserito nella repository. Spegni e riaccendi il GBA senza cartuccia.

Se la copia si interrompe o la ROM non viene riconosciuta, cancella `runtime/cache` e ripeti. Sono accettate solo cartucce italiane BPEI revisione 0.

## Avvio normale

1. Con il GBA acceso senza cartuccia, apri **14-AVVIA-SMERALDO.bat** e premi **INVIO** per caricare il residente 0.16.0 (oppure **S** per lo stabile 0.13.0). Mantieni cavo e selettore attuali.
2. Quando richiesto sul GBA, inserisci la cartuccia e premi **START**. Entra nella partita.
3. Quando il PC indica PRONTO, premi **SELECT + L + R** sul GBA. Il visualizzatore si apre su http://127.0.0.1:8765. La prima immagine arriva in circa un secondo. La prima volta che entri in un posto il PC impara la sua grafica; dalla seconda volta, anche nei giorni successivi, i cambi di scena sono piu rapidi (file `runtime/cache/blocchi-visti-2.bin`).

## Una sola sessione

Parti da **Ceneride, fuori dal Centro Pokemon**. Prima di ogni tratto seleziona la fase nella diagnostica della pagina:

- fermo per dieci secondi;
- cammina per circa un minuto a destra e sinistra, poi in verticale; corri tenendo B;
- entra nel Centro Pokemon e cammina anche dentro;
- esci, apri e chiudi squadra, Pokedex e menu; prova una battaglia se disponibile;
- apri le informazioni di un Pokemon della squadra e scorri le pagine; affronta almeno due incontri in erba alta fino al comando LOTTA;
- salva la partita dal menu con lo streaming attivo (il test in emulazione scrive un salvataggio identico, salvo il tempo di gioco);
- controlla che gioco e audio sul GBA restino fluidi come senza streaming, in particolare **entrando negli edifici** (li il programma nuovo trasmette mentre il gioco aspetta). SELECT + L + R mette in pausa e riprende la cattura per il confronto.

Alla fine premi **Scarica log** nella pagina: il browser scarica un unico file `log-<data-ora>.zip` (una copia resta in `dist/emerald-reports/<data-ora>`). Inviami quel solo file; non serve raccogliere cartelle. Puoi premerlo anche subito dopo un problema (per esempio dopo la battaglia), poi continuare. **Termina e salva rapporto** crea lo stesso zip in automatico. Il rapporto conta per ogni frame quanti blocchi e byte arrivano da mappe, palette, oggetti e copie dalla ROM, e quanti blocchi erano ancora in coda.

STREAM conta i tick ricevuti; NEL BROWSER conta le immagini presentate, senza contare il refresh della stessa immagine. IMMAGINI CAMBIATE esclude i frame visivamente identici. Le finestre sono di cinque secondi. Osserva anche a occhio: la fluidita percepita del movimento e il punto piu importante.

## Ripresa e OBS

R riprende il residente gia caricato nella stessa sessione della console (0.16.0 o 0.13.0: la pagina lo riconosce da sola). B carica la baseline 0.11.0 dopo spegnimento e riavvio senza cartuccia (non richiede la copia della cartuccia). Ripristina immagine richiede un riferimento completo mantenendo cavo e firmware.

Per OBS: sorgente Browser `http://127.0.0.1:8765/?clean=1`, dimensioni 240 x 160 o multipli. Il BAT deve restare aperto. Il buffer del browser e circa 200 ms.

## Cosa cambia e limiti

- **Cambi di scena.** Il GBA annuncia i blocchi con il loro hash; il PC li prende dalla grafica gia vista o dalla copia della cartuccia e l immagine esce quando il GBA li ha ricontrollati. Dopo una porta il GBA trasmette mentre il gioco aspetta l adattatore wireless, senza allungare l attesa.
- **Dissolvenze.** Il PC ricalcola la tavolozza dal colore e dal passo della dissolvenza e la usa solo se l hash coincide con quello del GBA.
- **Un pacchetto per VBlank** piu i pacchetti nel tempo libero del gioco, come nella 0.13.0. Finche mancano blocchi la pagina tiene l ultima immagine completa.
- **Copie dalla ROM.** Il GBA emette il riferimento solo dopo aver confrontato la VRAM con la ROM parola per parola.
- Il tasto SELECT + R + A (cadenza dimezzata) non esiste piu. SELECT + L + R resta.
- Gli effetti per scanline restano incompleti; gli effetti di lotta che cambiano parte di una tavolozza viaggiano come nella 0.13.0.
- Il pacchetto non contiene ROM o salvataggi e non richiede PROGETTO AMICO per funzionare.

Un futuro aggiornamento del Pico e consentito: il vincolo mantenuto e usare un solo firmware per multiboot e streaming durante tutta la procedura.
