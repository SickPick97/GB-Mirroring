**Dipendenze della prima consegna**

- Raspberry Pi Pico SDK 2.2.0: BSD-3-Clause, con ulteriori licenze nei componenti. Sorgenti completi locali in third_party/pico-sdk-2.2.0; [repository](https://github.com/raspberrypi/pico-sdk/tree/2.2.0).
- TinyUSB commit 86ad6e56c1700e85f1c5678607a762cfe3aa2f47: MIT. Sorgenti completi locali in third_party/tinyusb-86ad6e56c1700e85f1c5678607a762cfe3aa2f47; [repository](https://github.com/hathach/tinyusb/tree/86ad6e56c1700e85f1c5678607a762cfe3aa2f47). La struttura dei descrittori di usb_descriptors.c deriva dall'esempio video_capture, con attribuzione e licenza conservate nel file.
- Ninja 1.12.1: Apache-2.0; usato soltanto per la compilazione. [Release](https://github.com/ninja-build/ninja/releases/tag/v1.12.1).

Il firmware di test e distinto dal firmware Celio. RIPRISTINO-CELIO-PACCHETTO-AMICO.uf2 e la copia invariata del file fornito dall'utente, inclusa solo per il suo ripristino locale. ROM, salvataggi e asset di PROGETTO AMICO non sono inclusi nel firmware di test.

I file e le licenze preesistenti restano attribuiti ai rispettivi autori. Gli hash degli archivi di compilazione sono fissati in tools/prepare_dependencies.py.

**Banco Link 0.2.0**

Aggiornamento portatile 0.3.1: i due moduli sono copiati invariati in vendor/celio_transport e il runtime in runtime/python. Gli originali completi sono esclusi dalla repository. Il logo di header necessario alla compilazione e conservato separatamente in vendor/celio_transport/logo.bin. Vedi i README di queste cartelle per provenienza e limiti di distribuzione.

Il banco importa localmente i moduli mb_multi.py e usb_link.py del pacchetto dell'utente, conservandoli invariati e senza attribuirsi la loro paternita. Usa il relativo Python embedded e il firmware Celio originale. Il nuovo header multiboot contiene i byte di logo di avvio richiesti dal BIOS, ricavati dal file homebrew mbstub.gba fornito, non codice o asset delle cartucce Pokemon.

Unicorn 2.1.4 e usato solo come dipendenza di collaudo del codice ARM, in third_party/test-runtime; non e richiesto per il test fisico e non e incluso nei firmware. Le licenze del pacchetto sono conservate nella sua installazione locale. [Repository Unicorn](https://github.com/unicorn-engine/unicorn).

**Multi Profile 0.3.6**

Sequenza PIO master adattata dalla variante GBA del file Celio linkLayer_pio.c, copia di riferimento locale in analisi/fonti, progetto https://github.com/Celio-Link/Celio-Firmware (autori Celio e modifiche preesistenti del pacchetto). Non si dichiara che corrisponda esattamente al binario Celio ricevuto. Le 27 istruzioni conservano direzioni, temporizzazione e ordine dei bit; nuovo controllo Pico SDK e validatore GBMirroring. Uso nella repository privata; nessuna nuova licenza assegnata al codice derivato.
