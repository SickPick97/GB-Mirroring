# Verifica software 0.7.1

- 6 test residente ARM/protocollo: incluse reinizializzazione RCNT dopo transazione completa e richiesta NACK successiva.
- 4 test recupero: 9 combinazioni di inversione/inserimento/perdita di un bit, header e payload, stream frammentato; risorse esatte e transazione successiva conservate. Errore multiplo respinto, header incompleto atteso, CRC payload richiesto, ciclo delle richieste automatiche verificato.
- 10 test SD/viewer HTTP, 2 multiboot simulato, avvio reale con Python portatile da percorso con spazi: superati. Nessun dispositivo fisico aperto.
- mGBA: loader e rifiuto firma modificata; 90/90 confronti esatti su snapshot coerenti. Residente reale: 92/93 catture per 600 frame statici/con input, 600 VBlank gioco in entrambe le finestre. Dettagli in mgba.json. Non prova il trasporto elettrico, gli FPS hardware o tutta la partita.
- Manifest loader 5728 byte e runtime verificati; UF2 Pico 0.7.0 invariato rispetto alla release pubblicata.
- Replay delle code USB hardware precedenti documentato nel summary 0.7.0: dati parziali e sovrapposti, nessuna nuova misura hardware.

La nuova versione interviene sui ripristini evitabili. Non elimina il costo dei keyframe necessari, non certifica 10 FPS e non comprende la webcam UVC autonoma.
