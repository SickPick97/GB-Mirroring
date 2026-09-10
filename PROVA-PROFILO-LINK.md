# Profilo Link 0.3.5

Mantieni Celio sul Pico e il cavo fisso: piccolo nell'adattatore, grande nel GBA, selettore GBA, presa centrale vuota. Nessun nuovo firmware da caricare se hai appena completato la 0.3.4.

1. Chiudi tutti i programmi che usano il Pico. Spegni il GBA, slot vuoto.
2. Accendi il GBA e avvia 7-PROFILA-LINK.bat. Il multiboot e automatico.
3. Lascia acceso il GBA. Tre fasi da 30 s: timing 500, 125, 125. Poi screenshot conservativo. Non occorre premere tasti o invertire cavi.
4. Invia rapporto.json, console.txt e schermo-gba.bmp dalla nuova cartella dist/link-reports.

Durata prevista circa 2-3 minuti. Se non hai Celio, ripristina dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2 con BOOTSEL prima di avviare. In caso di errore conserva console e rapporto.

Il rapporto aggiunge conteggio trasferimenti GBA, byte/blocchi letti da USB, distribuzione delle dimensioni, durata media delle letture e coda campionata prima del parser. Le letture includono il tempo di attesa: non sono tempi sul filo e non misurano da sole il costo USB. I contatori ai confini possono comprendere pacchetti parziali/in coda. La coda massima e campionata, non un massimo assoluto. Il tempo CPU riguarda l'intero processo.

Questa versione non pretende di isolare ancora il tempo Pico. Serve a verificare accumulo lato PC e formato effettivo dei blocchi prima di modificare il firmware. Firmware e vendor invariati. La strumentazione puo influenzare la misura: confronto con 0.3.4 necessario. Normal a cavo invertito resta una diagnosi alternativa, non il setup finale.
