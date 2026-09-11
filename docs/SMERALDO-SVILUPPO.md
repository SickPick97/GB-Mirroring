# Smeraldo italiano: integrazione ancora aperta

La cartuccia dell utente e italiana e originale. Il loader del materiale ricevuto controlla BPEI e quattro firme, poi avvia il gioco preservando una regione EWRAM e sostituendo il vettore IRQ. Il profilo candidato in profiles/emerald-it-candidate.json riproduce le firme osservate, non certifica da solo l intera revisione. tools/emerald_profile.py esegue un controllo offline in sola lettura di un eventuale dump locale; non invia o modifica ROM e non abilita hook. Non serve eseguirlo per la prova 0.4.1.

Il banco 0.4.1 occupa circa 230 KiB per tre buffer: non puo essere inserito cosi nella RAM del gioco. La fase successiva deve esportare registri video, palette, OAM e blocchi VRAM modificati con memoria di lavoro limitata. Il PC deve ricostruire tile, sprite, priorita ed effetti del display. Leggere Mode 3 come RGB555 su Smeraldo produrrebbe dati errati.

Passaggi ancora necessari: verificare firme delle routine di avvio e memoria riservabile; payload residente con lavoro limitato per frame e ritorno corretto all IRQ originale; formato snapshot/delta grafico; renderer con confronto al risultato mGBA; prova hardware dal menu fino a overworld, battaglie e cambi scena. La frequenza del video e il rallentamento del gioco devono essere misurati separatamente. Nessuno di questi passaggi e dichiarato completato dalla release del banco.

Il trasporto FAST e il delta del banco servono a misurare quanto budget e disponibile. I circa 10 FPS del banco, se raggiunti, non dimostreranno automaticamente 10 FPS del gioco. UVC autonomo resta il risultato finale; anteprima PC e consentita durante lo sviluppo.
