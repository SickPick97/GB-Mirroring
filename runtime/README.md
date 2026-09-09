# Runtime Windows portatile

python e copiato dal runtime embedded del pacchetto fornito dall'utente, inclusi LICENSE.txt e le librerie USB presenti. Non vengono modificati gli eseguibili; non sono inclusi cache Python o dati di gioco.

Il file python313._pth mantiene l'isolamento standard del runtime. I nostri launcher aggiungono esplicitamente i percorsi tools e vendor/celio_transport. Il runtime e incluso per permettere il test privato su un altro PC senza installazioni globali.
