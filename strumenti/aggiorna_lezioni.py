"""Aggiorna l'orario lezioni dentro l'app Bus 21.

Uso: python3 aggiorna_lezioni.py <app.html> <ical_righe.txt> <uscita.html> [YYYY-MM-DD oggi]

<ical_righe.txt>: una riga per VEVENT nel formato  DTSTART|DTEND|SUMMARY|LOCATION
con DTSTART/DTEND in UTC (es. 20261009T070000Z), come restituite dal calendario iCal UniCH.

Regole:
- le lezioni con data < oggi restano come sono (storico);
- da oggi in poi vale il calendario iCal; le lezioni che prima c'erano e ora mancano
  vengono segnate come annullate (l'iCal esporta solo le lezioni pubblicate);
- gli eventi di tutto il giorno senza aula (festività, chiusure) sono ignorati;
- se i dati sembrano incompleti l'aggiornamento si ferma (exit 2) senza scrivere nulla.
"""
import json, re, sys
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
src, ical_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
today = sys.argv[4] if len(sys.argv) > 4 else datetime.now(ROME).strftime("%Y-%m-%d")

html = open(src, encoding="utf-8").read()
m = re.search(r"const LEZ = (\[.*?\]);\n", html, re.S)
if not m:
    sys.exit("ERRORE: non trovo 'const LEZ = [...]' nell'app")
old = json.loads(m.group(1))

cm = re.search(r"const COURSES = \{(.*?)\n\};", html, re.S)
if not cm:
    sys.exit("ERRORE: non trovo 'const COURSES' nell'app")
codes_by_name = {}
for code, name in re.findall(r'^\s*(\w+):\s*\{\s*name:\s*"([^"]+)"', cm.group(1), re.M):
    codes_by_name[name.upper().replace("À", "A'")] = code
codes_by_name.setdefault("REPORTING AZIENDALE E SOSTENIBILITA'", "REP")

floor_of = {}
for l in old:
    if l[5]:
        floor_of[l[4]] = l[5]

def to_local(s):
    dt = datetime.strptime(s.strip(), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(ROME)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

new_courses = {}
fresh = []
for raw in open(ical_path, encoding="utf-8"):
    raw = raw.strip()
    if not raw or "|" not in raw or raw.startswith(("TOTALE", "VEVENT")):
        continue
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 4:
        continue
    ds, de, summ, room = parts[:4]
    if not room:                      # festività / chiusure di Ateneo: tutto il giorno, senza aula
        continue
    d, s = to_local(ds)
    d2, e = to_local(de)
    key = summ.upper().strip()
    code = codes_by_name.get(key)
    if not code:
        code = new_courses.get(key)
        if not code:
            code = "C" + str(len(new_courses) + 1)
            while code in codes_by_name.values():
                code += "X"
            new_courses[key] = code
    fresh.append([d, s, e, code, room, floor_of.get(room, ""), 0])

future_fresh = [l for l in fresh if l[0] >= today]
old_future_live = [l for l in old if l[0] >= today and not l[6]]

# controlli di sicurezza: se l'iCal sembra troncato non tocco nulla
if old_future_live and not future_fresh:
    print("STOP: il calendario scaricato non contiene lezioni future, probabilmente il download e' fallito.")
    sys.exit(2)
k3 = lambda l: (l[0], l[1], l[3])
fresh_keys = {k3(l) for l in future_fresh}
vanished = [l for l in old_future_live if k3(l) not in fresh_keys]
if old_future_live and len(vanished) > 0.4 * len(old_future_live):
    print(f"STOP: sparirebbero {len(vanished)} lezioni su {len(old_future_live)}, probabile download incompleto.")
    sys.exit(2)

merged = [l for l in old if l[0] < today]
merged += future_fresh
for l in old:
    if l[0] >= today and k3(l) not in fresh_keys:
        merged.append([*l[:6], 1])     # c'era e ora non e' piu' pubblicata: annullata
merged.sort(key=lambda l: (l[0], l[1], l[3]))

# report differenze (solo da oggi in poi)
oldf = {k3(l): l for l in old if l[0] >= today}
newf = {k3(l): l for l in merged if l[0] >= today}
added = [newf[k] for k in newf if k not in oldf]
cancelled = [newf[k] for k in newf if newf[k][6] and k in oldf and not oldf[k][6]]
restored = [newf[k] for k in newf if not newf[k][6] and k in oldf and oldf[k][6]]
changed = [(oldf[k], newf[k]) for k in newf if k in oldf and oldf[k][2] != newf[k][2] or (k in oldf and oldf[k][4] != newf[k][4])]

html2 = html.replace(m.group(0), "const LEZ = " + json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + ";\n", 1)
if new_courses:
    entries = "".join(
        f'\n  {code}: {{ name: "{name.capitalize()}", prof: "", tipo: "nuovo" }},' for name, code in new_courses.items())
    html2 = html2.replace(cm.group(0), "const COURSES = {" + cm.group(1) + entries + "\n};", 1)
dd = datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y")
html2, n = re.subn(r'<span id="lezAgg">[^<]*</span>', f'<span id="lezAgg">{dd}</span>', html2)
if n != 1:
    sys.exit("ERRORE: non trovo il segnaposto della data di aggiornamento")
open(out, "w", encoding="utf-8").write(html2)

print(f"Lezioni totali: {len(merged)} (da oggi in poi: {len(newf)})")
print(f"Nuove: {len(added)}  Annullate: {len(cancelled)}  Ripristinate: {len(restored)}  Cambiate (orario/aula): {len(changed)}")
for l in added: print("  + nuova", l)
for l in cancelled: print("  - annullata", l)
for l in restored: print("  ↺ ripristinata", l)
for a, b in changed: print("  ~ cambiata", a, "->", b)
if new_courses: print("Corsi nuovi aggiunti (spenti di default):", new_courses)
