#!/usr/bin/env python3
"""
triage_sources.py — Classifica per pertinenza gli URL grezzi rastrellati.

Legge data/fonti_grezze.csv e assegna a ciascuna riga una categoria:
  core      -> parla del tema (aeroporto/Comani/scalo) E del filone CIVILE/riconversione
  contesto  -> cita l'aeroporto ma su altro (cerimonie 70° Stormo, Frecce, incidenti)
  offtopic  -> nessun aggancio al tema (rumore: link di sidebar, altri argomenti)

Output:
  data/fonti_triage.csv  (tutte le righe + colonna 'categoria', ordinate core->contesto->offtopic)
Stampa i conteggi. NON scarta nulla: 'offtopic' resta tracciato.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "fonti_grezze.csv"
OUT = ROOT / "data" / "fonti_triage.csv"

TOPIC = re.compile(r"aeroport|comani|\bscalo\b|aviosuperfic", re.I)
CORE = re.compile(
    r"civil|riconvers|terzo\s+(aeroport|scalo)|low.?cost|passegger|\bcargo\b|\bmerci\b|"
    r"aerostazion|de\s?amicis|pro.?aeroport|fazzone|martella|mozione|fattibil|masterplan|"
    r"ryanair|wizz|volotea|easyjet|\benac\b|pista|charter|frosinone|viterbo|"
    r"terzo\s+polo|scalo\s+merci|traffico\s+civil|rocca.*aeroport|aeroport.*rocca", re.I)
# segnali di contesto militare/altro (aiutano a NON marcare core)
NOISE = re.compile(r"frecce\s+tricolori|giurament|cerimoni|brevett|70.?\s*stormo|"
                   r"incident|caccia|elicotter\s+118|open\s+day|capodanno", re.I)


def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def slug(url: str) -> str:
    return deaccent(url.replace("-", " ").replace("/", " ").replace("_", " "))


def classify(row: dict) -> str:
    text = deaccent(row.get("titolo", "") + " ") + slug(row.get("url", ""))
    has_topic = bool(TOPIC.search(text))
    has_core = bool(CORE.search(text))
    if has_topic and has_core:
        return "core"
    if has_topic:
        return "contesto"
    return "offtopic"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Manca {SRC}: esegui prima harvest_sources.py")
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig", newline="")))
    for r in rows:
        r["categoria"] = classify(r)

    rank = {"core": 0, "contesto": 1, "offtopic": 2}
    rows.sort(key=lambda r: (rank[r["categoria"]], r.get("testata", ""), r.get("data", "")))

    fields = ["categoria", "testata", "data", "titolo", "url", "query_origine", "metodo"]
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    cats = Counter(r["categoria"] for r in rows)
    per_test = Counter(r["testata"] for r in rows if r["categoria"] == "core")
    print(f"Totale: {len(rows)}")
    for c in ("core", "contesto", "offtopic"):
        print(f"  {c:9} {cats.get(c,0)}")
    print("\nCORE per testata:")
    for t, n in per_test.most_common():
        print(f"  {t:24} {n}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
