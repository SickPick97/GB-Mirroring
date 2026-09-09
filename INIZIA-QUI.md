**Prima prova: il Pico diventa una webcam USB**

Il firmware e gia compilato per il tuo Raspberry Pi Pico RP2040. Non occorre installare programmi di sviluppo. Mostra barre colorate, un indicatore in movimento e un contatore: questa versione verifica il percorso Pico → USB → Fotocamera. Il video del GBA arrivera nelle fasi successive.

**Procedura**

1. Spegni il GBA e **scollega il cavo Link dall'adattatore**. Per questa prova serve solo l'adattatore collegato al PC via USB. Chiudi PassoTile, Celio e altri programmi che stanno usando l'adattatore.
2. Scollega l'USB del Pico. Tieni premuto il piccolo pulsante **BOOTSEL** sul modulo Pico e ricollega l'USB al PC. Rilascia il pulsante quando compare il disco **RPI-RP2**.
3. Copia sul disco RPI-RP2 questo file: [gbmirroring-uvc-test-v0.1.0.uf2](dist/gbmirroring-uvc-test-v0.1.0.uf2). La copia sostituisce il firmware sull'adattatore. Il disco scompare quando il Pico si riavvia: e normale.
4. Attendi alcuni secondi e apri l'app **Fotocamera** di Windows. Se mostra un'altra camera, usa il pulsante per cambiare fotocamera. Il nome previsto per il dispositivo e **GBMirroring - USB Test**; Windows puo anche mostrarlo genericamente come dispositivo video USB.
5. Cerca la scritta **GBMIRRORING**, le barre colorate e la scritta **USB TEST NO GBA VIDEO**. Il numero **FRAME** deve avanzare e il piccolo indicatore sotto le barre deve muoversi.
6. Lascia aperta l'anteprima per 10 minuti. Poi chiudi completamente Fotocamera e riaprila. Infine scollega e ricollega l'USB **senza BOOTSEL**, quindi verifica nuovamente l'immagine.

Non usare Zadig per questo firmware: la webcam deve usare il driver video integrato in Windows. Per il test non servono browser, Python, OBS, multiboot o cartucce.

**Come leggere la schermata**

| Indicazione | Significato |
|---|---|
| FRAME | Contatore dei trasferimenti di immagine completati dal firmware; deve continuare a cambiare. Non e una misura dei frame del GBA. |
| 10 FPS / 5 FPS | Frequenza negoziata con Windows. La modalita predefinita e 10 fps; sono disponibili anche 5 fps. |
| UP ... S | Secondi dall'accensione del Pico. Dopo un riavvio USB riparte. |
| RETRY | Tentativi di invio non accettati dallo stack USB, non errori misurati sul cavo. Se cresce continuamente, segnalalo. |

Un leggero sfocamento nell'anteprima ingrandita di Fotocamera puo dipendere dal ridimensionamento dei 240×160 pixel. Il test richiede che testo, colori e movimento siano presenti e stabili.

**Se non compare l'immagine**

Fai doppio clic su [CONTROLLA-USB.bat](CONTROLLA-USB.bat). Legge soltanto lo stato dei dispositivi e salva **dist/diagnosi-usb.txt**. Non cambia driver e non programma il Pico.

| Risultato | Passo successivo |
|---|---|
| RPI-RP2 resta visibile | Controlla che sia stato copiato il file UF2 dentro il disco, non soltanto scaricato sul PC. |
| Compare ancora Celio / 2FE3:000A | Il firmware di test non e attivo: ripeti BOOTSEL e la copia del file giusto. |
| Compare CAFE:4020 ma Fotocamera non lo mostra | Chiudi altre app che usano la camera, riapri Fotocamera e cambia dispositivo. Verifica nelle impostazioni Privacy di Windows che l'accesso alla fotocamera sia consentito. Conserva il rapporto USB. |
| Non compare alcun dispositivo previsto | Prova una porta USB diretta del PC e un cavo USB dati sicuramente funzionante. |
| Immagine nera, tagliata o contatore fermo | Riporta cosa vedi, eventuale codice errore di Fotocamera e il contenuto del rapporto USB. Evita di cambiare driver a tentativi. |

**Tornare a Celio / PassoTile**

Scollega l'USB, tieni BOOTSEL mentre la ricolleghi e copia nel disco RPI-RP2 [RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2](dist/RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2).

E una copia identica del celio.uf2 che mi hai fornito, verificata con SHA-256. **Non e un backup letto dal Pico**: se in seguito avevi caricato un firmware piu recente, per tornare esattamente a quello servira il relativo UF2. Il file originale in PROGETTO AMICO e rimasto invariato.

**Cosa comunicarmi dopo la prova**

- Il dispositivo compare in Fotocamera?
- Vedi tutte le barre e FRAME avanza? La schermata indica 10 o 5 FPS?
- Continua a funzionare dopo 10 minuti e dopo chiusura/riapertura dell'app?
- Funziona dopo aver scollegato e ricollegato l'USB senza BOOTSEL?
- Se c'e un problema: messaggio/codice errore e rapporto dist/diagnosi-usb.txt.

**Stato della consegna**

Sorgenti C compilati con Arm GCC 14.3.1; controlli degli avvisi attivi sul nostro codice. Verificati dal binario finale: checksum del bootloader, vettori di avvio, indirizzi e contenuto dei blocchi UF2, formato YUY2, descrittori UVC, risoluzione e banda degli endpoint. Il [rapporto automatico](dist/verifica-firmware.json) e incluso.

La prova fisica di enumerazione e streaming sul tuo Pico deve ancora essere fatta: la compilazione e i controlli statici non la sostituiscono. Una volta verificata questa uscita USB, il passo successivo e il banco Link con dati noti e il GBA collegato.

