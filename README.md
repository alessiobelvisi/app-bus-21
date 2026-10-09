# Bus 21 · le mie fermate

App web personale per la **linea 21 TUA** (Pescara Terminal ↔ Francavilla al Mare) e l'orario delle lezioni del 3° anno di Economia, Imprese e Mercati Finanziari (UniCH, Pescara).

- **Bus**: prossimi passaggi alle fermate scelte, con conto alla rovescia e scelta automatica dell'orario (feriale con/senza scuola, festivo, Natale/Pasqua/Capodanno).
- **Lezioni**: orario settimanale dei corsi scelti, con il bus da prendere per arrivare in tempo e quello per tornare.

Si apre `index.html` in qualsiasi browser: è un unico file, senza server.

## Fonti dei dati
- Orari bus: tabella ufficiale TUA della linea 21, valida dal 19/09/2025 (orari programmati, non in tempo reale).
- Calendario scolastico Abruzzo 2026/27 (per le corse scolastiche).
- Lezioni: calendario pubblico University Planner UniCH, 3° anno L-33.

## Struttura
- `index.html`: l'app.
- `dati/`: orari estratti (JSON).
- `strumenti/parse.py`: estrae le corse dal PDF TUA (testo di `pdftotext -layout`).
- `strumenti/aggiorna_lezioni.py`: aggiorna le lezioni dentro `index.html` dal calendario iCal.
- `strumenti/template.html`: sorgente dell'app (`__DATA__` e `__LEZ__` vengono sostituiti con i dati).

## Aggiornamento automatico delle lezioni
Ogni notte a mezzanotte (ora italiana) l'azione GitHub `.github/workflows/aggiorna-lezioni.yml` esegue
`strumenti/aggiorna_da_api.py`: scarica il calendario pubblico UniCH, aggiorna le lezioni dentro `index.html`
(annullate, cambi d'aula, lezioni nuove) e salva le modifiche. Si può avviare anche a mano da
**Actions → Aggiorna lezioni → Run workflow**. Se il download fallisce, l'app non viene toccata.
