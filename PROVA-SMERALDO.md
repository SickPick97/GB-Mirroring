# Avvio e collaudo unico (residente 0.11.0, pacchetto 0.11.1)

[English quick start](docs/QUICKSTART.en.md). Il pacchetto 0.11.1 aggiorna documentazione e licenze; i binari restano invariati.

Pacchetto pronto, senza compilazione. Corregge il trasporto delle porzioni di mappa che cambiano durante il cammino. Nella prova emulata orizzontale di Ceneride passa da 13,64 a 21,35 catture/s (+57%). Il ciclo principale del gioco mantiene 1198 aggiornamenti in 1200 frame, come senza residente. **Non abbiamo ancora raggiunto o verificato 30 FPS costanti nel browser.**

## Avvio

1. Estrai tutto lo ZIP 0.11.1 in una nuova cartella scrivibile. Chiudi il vecchio BAT e la vecchia pagina.
2. Il Pico unificato **0.7.0 resta compatibile**: per questa versione non occorre riflasharlo. Mantieni cavo e selettore attuali. Se parti da un Pico con firmware diverso, usa `dist/gbmirroring-unified-v0.7.0.uf2` con BOOTSEL.
3. Spegni il GBA, togli la cartuccia e riaccendilo. Apri **14-AVVIA-SMERALDO.bat** e premi **INVIO**, per caricare il nuovo residente. Non scegliere R al primo avvio della nuova versione.
4. Quando richiesto sul GBA, inserisci Smeraldo italiano originale e premi START. Entra nella partita.
5. Quando il PC indica PRONTO, premi **SELECT + L + R** sul GBA. Il visualizzatore si apre su http://127.0.0.1:8765. Attendi la prima immagine.

## Una sola sessione

Parti da **Ceneride, fuori dal Centro Pokemon**. Prima di ogni tratto seleziona la fase nella diagnostica della pagina:

- cammina per circa un minuto a destra e sinistra, poi in verticale;
- entra nel Centro Pokemon e cammina anche dentro;
- esci, apri e chiudi squadra e menu; prova una battaglia se disponibile;
- controlla che gioco e audio sul GBA restino fluidi. SELECT + L + R mette in pausa e riprende la cattura per il confronto.

Concludi con **Termina e salva rapporto** e invia l'intera cartella `dist/emerald-reports/<data-ora>`. I nuovi contatori registrano automaticamente quanti blocchi e byte riguardano mappe, palette, oggetti e altre risorse: non serve una prova separata di misura.

STREAM conta aggiornamenti verificati ricevuti; NEL BROWSER conta immagini presentate, senza contare il refresh della stessa immagine. IMMAGINI CAMBIATE esclude i frame visivamente identici. Le finestre sono di cinque secondi; queste metriche non misurano gli FPS del gioco fisico.

## Ripresa e OBS

R riprende il residente gia caricato nella stessa sessione della console. B carica la baseline 0.8.0 dopo spegnimento e riavvio senza cartuccia. Ripristina immagine richiede un riferimento completo mantenendo cavo e firmware.

Per OBS: sorgente Browser `http://127.0.0.1:8765/?clean=1`, dimensioni 240 x 160 o multipli. Il BAT deve restare aperto. Il buffer del browser e circa 200 ms.

## Cosa cambia e limiti

Le mappe usano patch di gruppi di quattro colonne, invece di inviare sempre il blocco completo. La ricostruzione controlla entrambe le firme del blocco, oltre al CRC del pacchetto: una firma compatta in collisione provoca recupero, non l'accettazione della patch errata. Le patch senza colonne rilevate ripiegano sui codec completi.

Il dizionario scende da 128 a 64 voci per lasciare spazio alle firme delle mappe; registri/OAM restano differenziali. Il limite resta 155 parole per intervento. In una prova piu favorevole a Porto Selcepoli la media emulata scende da 33,20 a 31,46: il beneficio non e uniforme. Ceneride verticale passa da 21,25 a 21,95; il Centro da 18,96 a 20,76. Squadra e cambi scena rimangono sotto il target. Gli effetti per scanline sono ancora incompleti.

120 scene emulatore con movimento e menu sono state inviate dal codice ARM ed esattamente ricostruite sul PC. La prova mantiene ogni scena stabile durante l'invio: controlla il codec, non certifica la coerenza temporale o le prestazioni sul collegamento fisico. Il pacchetto non contiene ROM o salvataggi e non richiede PROGETTO AMICO per funzionare.

Un futuro aggiornamento del Pico e consentito: il vincolo mantenuto e usare un solo firmware per multiboot e streaming durante tutta la procedura.
