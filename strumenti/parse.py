"""Estrae tutte le corse della linea 21 dal PDF ufficiale TUA (testo pdftotext -layout)."""
import json, re, sys

TIME = re.compile(r"\b(\d{2}:\d{2})\b")
CODES = {"UFRIN", "URBSC", "NSCIN", "FSINV", "00021"}

lines = open(sys.argv[1], encoding="utf-8").read().splitlines()

pages = []  # (direction, codes, numbers, rows[(stop, [times])])
cur = None
for ln in lines:
    if "TERMINAL - FRANCAVILLA FORO" in ln:
        direction = "ANDATA" if "ANDATA" in ln else "RITORNO"
        cur = {"dir": direction, "codes": None, "nums": None, "rows": []}
        pages.append(cur)
        continue
    if cur is None:
        continue
    s = ln.strip()
    if s.startswith("Validit"):
        cur["codes"] = s.split()[1:]
        continue
    if s.startswith("Numero corsa"):
        cur["nums"] = s.split()[2:]
        continue
    times = TIME.findall(ln)
    if times and cur["codes"]:
        m = TIME.search(ln)
        name = ln[: m.start()].strip()
        name = re.sub(r"\s+(Da|A)$", "", name).strip()
        cur["rows"].append((name, times))

problems = []
trips = {}
stops_order = {"ANDATA": [], "RITORNO": []}
for p in pages:
    n = len(p["codes"])
    assert all(c in CODES for c in p["codes"]), p["codes"]
    assert len(p["nums"]) == n, (len(p["nums"]), n)
    for name, times in p["rows"]:
        if len(times) != n:
            problems.append((p["dir"], name, len(times), n))
        if name not in stops_order[p["dir"]]:
            stops_order[p["dir"]].append(name)
    for i in range(n):
        key = p["nums"][i]
        t = {name: times[i] for name, times in p["rows"] if len(times) == n}
        trips[key] = {"dir": p["dir"], "code": p["codes"][i], "num": key, "times": t}

print("pagine:", len(pages), " corse:", len(trips))
for d in ("ANDATA", "RITORNO"):
    ts = [t for t in trips.values() if t["dir"] == d]
    from collections import Counter
    print(d, len(ts), Counter(t["code"] for t in ts), "fermate:", len(stops_order[d]))
print("righe con conteggio anomalo:", problems[:20], len(problems))

json.dump({"stops": stops_order, "trips": list(trips.values())},
          open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
