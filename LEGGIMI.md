# App bus 21 (casa · università · mensa)

- `index.html`: l'app. Si apre con un doppio clic in qualsiasi browser e funziona anche senza internet.
- `dati/orari-linea-21.json`: gli orari della linea 21 solo per le tue fermate.
- `dati/linea-21-tutte-le-fermate.json`: tutte le 218 corse con tutte le fermate.
- `strumenti/parse.py`: estrae gli orari dal PDF ufficiale TUA (testo ottenuto con `pdftotext -layout`).
- `strumenti/template.html`: il codice dell'app; `__DATA__` viene sostituito con il contenuto di `orari-linea-21.json`.

Fonte: tabella ufficiale TUA linea 21, valida dal 19/09/2025.
Calendario scolastico Abruzzo 2026/27: lezioni dal 16/09/2026 al 09/06/2027, vacanze dal 23/12 al 06/01 e dal 25/03 al 30/03, ponte il 07/12.
