"""Aggiorna le lezioni dentro index.html leggendo il calendario pubblico UniCH (University Planner).

Uso:  python strumenti/aggiorna_da_api.py index.html [risposta_api.json]
Il secondo argomento serve solo per i test: se manca, i dati vengono scaricati dal sito dell'universita'.

Regole:
- le lezioni dei giorni passati restano come sono;
- da oggi in poi vale il calendario dell'universita' (lezioni annullate comprese);
- se una lezione futura sparisce del tutto dal calendario viene segnata come annullata;
- se il download sembra incompleto lo script si ferma con errore e non modifica nulla.
Scrive anche dati/lezioni-3anno-2026-27.json e stampa le novita'.
"""
import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
API = "https://unich.prod.up.cineca.it/api/Impegni/getImpegniCalendarioPubblico"
LINK_ID = "5e71face7c2af0001828a278"      # III anno L-33 Economia, Imprese e Mercati Finanziari
CLIENTE_ID = "5a65a9ebd9fe4f6d0ccf9df6"   # Universita' G. d'Annunzio
FLOOR = {"piano -1": "-1", "piano terra": "T", "piano 1": "1", "piano 2": "2", "livello 1": "1"}

app_path = Path(sys.argv[1])
now = datetime.now(ROME)
today = now.strftime("%Y-%m-%d")


def download():
    body = {
        "mostraImpegniAnnullati": True, "mostraIndisponibilitaTotali": True, "filtroSfondoId": None,
        "linkCalendarioId": LINK_ID, "clienteId": CLIENTE_ID, "pianificazioneTemplate": False,
        "dataInizio": now.astimezone(timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z"),
        "dataFine": "2027-09-30T00:00:00.000Z",
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "app-bus-21 (aggiornamento orario lezioni personale)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


events = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else download()
if isinstance(events, dict):
    events = events.get("impegni") or events.get("data") or []
if not isinstance(events, list):
    sys.exit("ERRORE: risposta inattesa dal calendario")

html = app_path.read_text(encoding="utf-8")
m = re.search(r"const LEZ = (\[.*?\]);\n", html, re.S)
cm = re.search(r"const COURSES = \{(.*?)\n\};", html, re.S)
if not m or not cm:
    sys.exit("ERRORE: non trovo i dati delle lezioni dentro index.html")
old = json.loads(m.group(1))

codes_by_name = {}
for code, name in re.findall(r'^\s*(\w+):\s*\{\s*name:\s*"([^"]+)"', cm.group(1), re.M):
    codes_by_name[name.upper().replace("À", "A'")] = code
codes_by_name.setdefault("REPORTING AZIENDALE E SOSTENIBILITA'", "REP")


def local(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ROME)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


new_courses, fresh = {}, []
for ev in events:
    name = (ev.get("nome") or "").strip()
    if not name:                       # festivita' e chiusure di Ateneo
        continue
    d, s = local(ev["dataInizio"])
    _, e = local(ev["dataFine"])
    key = name.upper()
    code = codes_by_name.get(key) or new_courses.get(key)
    if not code:
        code = "C" + str(len(new_courses) + 1)
        while code in codes_by_name.values():
            code += "X"
        new_courses[key] = code
    aula = next((r["aula"] for r in ev.get("risorse") or [] if r.get("aula")), None)
    room = aula.get("descrizione", "") if aula else ""
    floor = FLOOR.get(((aula or {}).get("piano") or {}).get("descrizione", ""), "")
    fresh.append([d, s, e, code, room, floor, 1 if ev.get("stato") == "A" else 0])

k3 = lambda l: (l[0], l[1], l[3])
future_fresh = [l for l in fresh if l[0] >= today]
old_future_live = [l for l in old if l[0] >= today and not l[6]]
fresh_keys = {k3(l) for l in future_fresh}
vanished = [l for l in old_future_live if k3(l) not in fresh_keys]
if old_future_live and not future_fresh:
    sys.exit("STOP: il calendario non contiene lezioni future, probabilmente il download e' fallito")
if old_future_live and len(vanished) > 0.4 * len(old_future_live):
    sys.exit(f"STOP: sparirebbero {len(vanished)} lezioni su {len(old_future_live)}, probabile download incompleto")

merged = [l for l in old if l[0] < today] + future_fresh
merged += [[*l[:6], 1] for l in old if l[0] >= today and k3(l) not in fresh_keys]
merged.sort(key=lambda l: (l[0], l[1], l[3]))

oldf = {k3(l): l for l in old if l[0] >= today}
newf = {k3(l): l for l in merged if l[0] >= today}
report = []
for k, l in newf.items():
    o = oldf.get(k)
    if not o:
        report.append(f"+ nuova {l}")
    elif l[6] and not o[6]:
        report.append(f"- annullata {l}")
    elif o[6] and not l[6]:
        report.append(f"ripristinata {l}")
    elif o[2] != l[2] or o[4] != l[4]:
        report.append(f"~ cambiata {o} -> {l}")

html2 = html.replace(m.group(0), "const LEZ = " + json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + ";\n", 1)
if new_courses:
    entries = "".join(f'\n  {c}: {{ name: "{n.capitalize()}", prof: "", tipo: "nuovo" }},' for n, c in new_courses.items())
    html2 = html2.replace(cm.group(0), "const COURSES = {" + cm.group(1) + entries + "\n};", 1)
html2 = re.sub(r'<span id="lezAgg">[^<]*</span>', f'<span id="lezAgg">{now.strftime("%d/%m/%Y")}</span>', html2)
app_path.write_text(html2, encoding="utf-8")
data_dir = app_path.parent / "dati"
if data_dir.is_dir():
    (data_dir / "lezioni-3anno-2026-27.json").write_text(
        json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

print(f"Eventi scaricati: {len(fresh)} lezioni. Da oggi in poi: {len(newf)}.")
print("\n".join(report) if report else "Nessuna novita'.")
if new_courses:
    print("Corsi nuovi (si attivano in Lezioni -> I miei corsi):", ", ".join(n.capitalize() for n in new_courses))
