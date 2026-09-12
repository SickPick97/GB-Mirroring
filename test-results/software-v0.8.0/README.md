# Verifica software 0.8.0

- Residente ARM: sei test, inclusi esatta ricostruzione delle risorse, limite 155 parole per intervento, reset RCNT e NACK.
- Codec LZ: due test. Encoder ARM compilato eseguito su 43 blocchi sintetici, dati ricostruiti esattamente, incomprimibili lasciati intatti; controllo area inferiore dello stack. Decoder rifiuta riferimenti impossibili, lunghezze e token invalidi.
- Quattro test di recupero CRC, dieci SD/viewer HTTP, due multiboot simulato. Endpoint after evita trasferimento del frame gia visualizzato; metriche distinguono frame ricevuti e immagini cambiate.
- UI verificata nel browser con fixture sintetica e metriche simulate, mai presentate come risultati hardware. Vista pulita verificata. Nessun dispositivo USB/Link aperto.
- mGBA: firma loader, 90 confronti grafici esatti da snapshot coerenti; residente reale in finestre statiche/con input, dettagli in mgba.json. I confronti grafici non sono un test elettrico del nuovo codec; il codec e verificato separatamente con esecuzione ARM.
- Compressione su blocchi reali selezionati dalla coda USB: compression.json. I dati grafici grezzi rimangono locali; il campione non rappresenta tutte le scene ne l intero stream.

Raddoppio FPS hardware e fluidita della console ancora da collaudare. Versione Pico invariata 0.7.0; nuovi loader e programma PC 0.8.0. La pagina web e l uscita scelta dall utente.
