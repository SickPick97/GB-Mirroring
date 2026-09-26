# Celio publication audit / Verifica pubblicazione Celio

Updated 2026-09-26. Application-source gap resolved by the supplied archives; attribution and build-reproduction limits are recorded below.

## English

The supplied gen3-poke-multiplayer archive declares GPL-3.0 and includes the full Celio patch, base commit and build instructions. Its release celio.uf2 is byte-identical to our historical recovery UF2: SHA-256 735bf7334c52411f4fba0f4370404040c890ad00d3a95b2fe8612a29560bff1d.

The patch applies to all 11 target files at Celio commit f67733c293defc3d77185101cb00d3ce19ef3284. Base archive, unmodified patch, license, provenance and portable source reconstruction are included in vendor/celio_legacy_source. Zephyr commit was recovered from the binary build identifier. The supplier identifies these application sources with this binary; a bit-identical rebuild has not been performed, and its frozen dependency manifest and original ELF were not supplied.

The supplied firmware README calls modifications in usbLinkCommand.cpp, usbSection.hpp and raw-relay drop counters pre-existing third-party changes. No individual author or external repository is named. Searches of supplied documentation found no further attribution. The current USB callback file in Celio and the two listed public forks (TabsN/Celio-Firmware, GB-Link/GBLink-Firmware) does not contain the same queue changes. This limited search does not establish that no other origin exists. We preserve the supplier's GPL declaration and explicitly leave individual authorship unresolved; AI use is not evidence of provenance.

Current GBMirroring firmware has its own sources and a separate pinned Celio PIO reference. All 27 inherited PIO words match. The legacy UF2 is not required by the current launcher. No history rewrite or firmware replacement is part of this publication preparation.

The imported scope is source and notices needed for our existing components, not the friend's whole project. Cooperative payloads, map assets and other release binaries remain local. Their source archive is not executed or automatically published. Root THIRD_PARTY.md lists included dependencies and their licenses; it does not assign GPL rights to Nintendo logos or screenshots.

## Italiano

L'archivio ricevuto dichiara GPL-3.0 e contiene patch Celio completa, commit base e istruzioni. Il celio.uf2 ricevuto coincide esattamente con quello storico (hash sopra). Le patch si applicano a tutti gli 11 file del commit indicato. Base, patch invariata, licenza e ricostruzione portatile dei sorgenti sono inclusi. Il commit Zephyr proviene dalla stringa del binario.

Il contributore associa questi sorgenti al binario. Non abbiamo eseguito una ricompilazione identica; mancano manifest congelato e ELF originali. Tre modifiche sono descritte come preesistenti e di terzi, senza nome o repository. Nei documenti ricevuti non risultano altre attribuzioni. Il file USB corrente di Celio e dei due fork pubblici esaminati non contiene quelle modifiche; questa ricerca limitata non esclude altre origini. Conserviamo la dichiarazione GPL del fornitore, senza inventare autori. L'uso di AI non dimostra la provenienza.

Il firmware corrente ha sorgenti propri e riferimento PIO Celio separato, verificato sulle 27 parole. Non richiede il vecchio UF2. Nessuna riscrittura della cronologia o sostituzione del firmware. Importiamo solo ciò che serve ai componenti esistenti; cooperativa, asset della mappa e altri binari restano locali. Licenze e crediti sono in THIRD_PARTY.md, senza attribuire diritti GPL sul materiale Nintendo.
