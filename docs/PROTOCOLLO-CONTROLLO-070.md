# Controllo 0.7.0

Il formato grafico resta 0x600. Nel campo mode di END il byte basso 2 identifica il residente 0.7.0; bit 8 indica risposta rilevata nella finestra precedente. Non implica correttezza di ogni richiesta.

Dopo END il GBA invia una parola zero per scaricare i bit finali anche quando il ricevitore e disallineato. Poi rilascia SD, mantiene SC alto per la finestra di qualificazione e campiona due bit. La prima risposta bassa identifica il Pico; la seconda alta richiede un nuovo keyframe. Due livelli alti indicano assenza di risposta. Seguono 14 impulsi idle per completare un gruppo di 16 fronti.

Il Pico abilita questo percorso solo dopo CONTROL e un END 0.7.0 con header e payload CRC validi. La macchina PIO qualifica SC alto per 64 istruzioni a divisore 16; i normali impulsi video devono restare piu brevi. Precarica il valore, abilita la direzione SD, attende i fronti previsti, rilascia SD e rimane inattiva fino al riarmo. Watchdog software a 1,5 ms rilascia la linea in caso di slot incompleto. STOP e disconnessione rilasciano tutte le linee.

RESYNC accoda la richiesta per il prossimo END riconosciuto. Il PC limita le richieste automatiche a una ogni quattro secondi. Il recupero resta un keyframe completo, non una riparazione per singola risorsa; il suo tempo dipende dalla scena e dalla banda. Senza conferma il residente conserva il keyframe ogni 120 catture; con conferma l'intervallo di sicurezza diventa 3600.

Collaudi software: istruzioni PIO effettivamente configurate, nessun pilotaggio durante impulsi brevi, bit di risposta e rilascio dopo uno slot; residente ARM che riceve NACK e produce keyframe. Restano da collaudare orientamento reale delle linee, pull-up, tempi e concorrenza DMA sulla console. Nessun test software invia dati a dispositivi.
