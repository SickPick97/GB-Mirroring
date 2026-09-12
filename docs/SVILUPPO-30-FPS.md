# Stato dello sviluppo dopo 0.8.0

Non e una nuova release hardware. Il minimo di circa 30 FPS rimane da raggiungere sul collegamento; nessun nuovo flash o collaudo fisico richiesto per questo checkpoint.

## Implementato e verificato sul PC

- Renderer mGBA diretto in C: niente esecuzione di due frame homebrew per ogni immagine e conversione pixel nativa. DLL Windows x64 con runtime MSVC statico, sorgenti necessari e licenza inclusi; build offline con `python tools/build_native_renderer.py` su una macchina con Visual Studio 2022 e CMake.
- Stesso formato RGB565 interno del riferimento libretro: importante per l'arrotondamento delle dissolvenze. Uscita RGB555 invariata.
- 900 immagini di una sequenza da salvataggio locale in emulazione: zero differenze rispetto al gioco; trenta confronti aggiuntivi con il vecchio renderer, zero differenze. Mediana nativa 1,365 ms, p95 2,452 ms su questa macchina. Non sono FPS sul GBA fisico. Dati commerciali e stati emulatori restano esclusi dalla repository.
- Test sintetici dei sei modi video e di sprite, finestre, blending e mosaico. Gli effetti che variano i registri durante le scanline rimangono un limite della cattura a snapshot: nella sequenza di introduzione esistono differenze gia presenti nel percorso precedente.
- Invio WebSocket binario, code limitate, controllo ping/close, presentazione requestAnimationFrame con clock sorgente e buffer 200 ms. Pausa, wrap del contatore, sospensione browser e smaltimento arretrati gestiti. Statistiche browser separate da ricezione/rendering; nessuna interpolazione.
- Gestore delle dipendenze immutabili `graphics_resources.py`, ancora separato dal trasporto attivo: attende risorse mancanti senza sostituirle con una versione successiva; rifiuta epoche/ordinamenti errati e contenuti corrotti, limita memoria e presentazioni in attesa. Gli identificativi SHA256 sono per ora lato host, non un formato Link gia implementato.

## Lavoro necessario prima della consegna integrata

1. Concludere formato compatto Link e residente a stati rapidi: la pipeline attiva usa ancora transazioni 0.8.0. Renderer e buffer non aumentano da soli il numero di campioni GBA.
2. Validare gli osservatori delle copie effettivamente completate, anche fuori dall'overworld; una richiesta DMA pendente non certifica una versione VRAM. Non pubblicare OAM nuovo con tile non ancora disponibili.
3. Integrare cache locale automatica e recupero delle risorse nel trasporto. Nessun dump/precaricamento cartuccia e implementato in questo checkpoint.
4. Rientrare nella RAM riservata e misurare CPU, byte reali e cadenza nelle scene richieste. Il residente attuale lascia soltanto 448 byte prima dello stack: non aggiungere buffer senza rivedere disposizione e controlli del linker.
5. Preparare binari con una nuova versione, manifest, aggiornamento portatile e un unico test guidato. Non sovrascrivere le release precedenti.

## Ripresa tecnica

File nuovi: `native/renderer`, `runtime/native`, `tools/native_renderer.py`, `tools/frame_hub.py`, `tools/playout.js`, `tools/graphics_resources.py` e relativi test. Il viewer principale usa gia renderer e WebSocket nella versione di sviluppo; il tag 0.8.0 resta invariato.

`tools/evaluate_fast_trace.py` richiede ROM/stato locali espliciti. `build/emerald/start.state` e l'introduzione, non l'overworld. La sequenza positiva usa `build/emerald/fast-field.state`, preparata con lo stesso bootstrap del test di integrazione e il salvataggio locale. La stima di 7655 B/s e un limite teorico con cache ideale, non un protocollo trasmesso ne una misura hardware. Il rapporto ripulito conserva soltanto contatori.

## Prova isolata di memoria del residente

`tools/probe_resident_budget.py` compila soltanto in build/emerald-next. C in Thumb, trasporto/hash ARM mantenuti; ritorni BX e simboli funzione espliciti per interworking ARMv4T. Non modifica i sorgenti firmware stabili o i binari dist.

Residente 4560 -> 3680 byte; spazio prima dello stack 448 -> 1328 byte, recuperati 880. Il confronto locale da stato identico registra 179 catture / 600 VBlank sia fermo sia con input direzionale, contro 178/179 della baseline. Sono conteggi mGBA, non FPS fisici. La cadenza resta quella precedente: questa prova libera memoria, non raggiunge da sola il target.

Comandi di verifica: `python tools/test_resident_candidate.py` per protocollo ARM, codec, feedback e massimo 155 parole; `python tools/test_resident_budget.py --rom <ROM locale> --state <stato locale>` per confronto emulato. Prima build Thumb respinta per un salto interworking mancante; versione corretta richiede dichiarazioni `.type ..., %function` e ritorni `bx lr` nelle routine ARM. Non trasferire alla cieca soltanto il flag -mthumb.
