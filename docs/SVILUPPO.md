**GBMirroring 0.1.0 — firmware UVC di prova**

Aggiornamento: l'utente ha confermato immagine, movimento e riapertura in Fotocamera; dettagli in docs/VALIDAZIONE-HARDWARE.md. Il nuovo banco Link 0.2.0 e descritto in PROVA-LINK.md e docs/LINK-TEST-SVILUPPO.md. Il testo seguente documenta la prima consegna UVC.

Questa consegna implementa la fase 1 del piano: sorgente video sintetica sul Pico e UVC nativo. Non contiene ancora un acquisitore GBA, un sender multiboot o profili di cartucce.

La cartella firmware/uvc-test contiene il ciclo di acquisizione/invio, i descrittori e il generatore YUY2. main.c mantiene un solo buffer da 76.800 byte, che non modifica durante il trasferimento; riparte alla nuova negoziazione e dopo un arresto dello stream. Il generatore mostra testo e un marker mobile. Le callback vengono eseguite nel task TinyUSB sullo stesso core; gli interrupt USB accodano gli eventi. Non e attivo stdio UART, per evitare di usare GP0/GP1, e GP0–GP4 sono inizializzati come ingressi senza pull. Solo il LED GP25 viene pilotato.

USB: identificativo di sviluppo TinyUSB CAFE:4020, distinto da Celio 2FE3:000A; UVC 1.5, YUY2 240×160, intervalli discreti di 100/200 ms, endpoint isocrono IN 0x81 da 1023 byte per frame USB. Nessuna interfaccia CDC, HID, MSC o vendor. Il VID/PID di esempio non costituisce un'identita commerciale assegnata al progetto.

Il firmware risponde a Windows con numero seriale stabile ricavato dall'identificativo univoco della flash del Pico. Il contatore misura trasferimenti completati nello stack, non una conferma che Fotocamera abbia visualizzato tutti i pixel. L'UF2 e generato a partire dal BIN del linker, con family ID RP2040; non viene effettuato alcun flash automatico.

**Ricompilazione su Windows**

Nel PC attuale sono gia disponibili Python 3.9, CMake 4.1.2 e Arm GNU Toolchain 14.3.Rel1. Su un altro PC occorrono Python >=3.9, CMake >=3.20 e arm-none-eabi-gcc nel PATH. Ninja viene preparato localmente dallo script.

Eseguire COMPILA.bat dalla radice, oppure in PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1
```

La compilazione scarica le dipendenze solo quando gli archivi mancano, ne verifica gli hash, prepara i file in third_party e tools/ninja, compila, genera l'UF2 e verifica il binario. Downloads, SDK e build sono locali al progetto: nessuna installazione globale. Gli archivi hanno versione/commit e SHA-256 fissati in tools/prepare_dependencies.py. La versione TinyUSB e esattamente il submodule pin del Pico SDK 2.2.0.

Gli script make_uf2.py e verify_firmware.py non usano PyUSB e non contattano hardware. Il verificatore legge i descrittori dal BIN usando gli indirizzi dei simboli dell'ELF, invece di fidarsi dei soli header sorgenti. Controlla anche il CRC del boot2, la destinazione del reset, il round-trip UF2/BIN e la catena dei terminali UVC.

**Limiti delle verifiche**

Il test su Windows deve ancora verificare enumerazione, driver usbvideo, apertura dell'app Fotocamera, riapertura e stabilita. Il buffer da 1023 byte permette il budget teorico richiesto a 10 fps; non e un benchmark del controller USB reale. Le lettere FRAME e RETRY servono a discriminare una immagine congelata da una trasmissione attiva e a raccogliere un riscontro concreto.

La prossima fase deve introdurre prima un homebrew diagnostico con dati noti, multiboot e misura Link. La cattura di Smeraldo/Verde Foglia viene dopo la verifica del trasporto. Il risultato UVC sintetico non deve essere presentato come video della console.
