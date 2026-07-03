#!/usr/bin/env python3
"""
archive_sources.py — Copia storica locale (PDF) di ogni risorsa web citata.

Per ogni URL genera un PDF tramite Chrome headless e aggiorna un manifest che
collega l'URL originale al file PDF locale. Idempotente: URL gia' archiviati
vengono saltati (usa --force per rigenerare).

Uso:
    # da un file di URL (uno per riga, righe che iniziano con # ignorate)
    python archive_sources.py --input fonti.txt

    # da URL passati a riga di comando
    python archive_sources.py https://esempio.it/articolo1 https://esempio.it/articolo2

    # da un CSV con colonne: url,titolo,testata,data_articolo (titolo/testata/data opzionali)
    python archive_sources.py --csv fonti.csv

Output:
    archive/pdf/<testata>_<data>_<slug>_<hash>.pdf
    archive/manifest.csv
    archive/manifest.json
    archive/errori.log
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# --- Percorsi -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # aeroporto-latina/
ARCHIVE_DIR = ROOT / "archive"
PDF_DIR = ARCHIVE_DIR / "pdf"
MANIFEST_JSON = ARCHIVE_DIR / "manifest.json"
MANIFEST_CSV = ARCHIVE_DIR / "manifest.csv"
ERROR_LOG = ARCHIVE_DIR / "errori.log"

# --- Chrome -------------------------------------------------------------------
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    sys.exit("ERRORE: nessun Chrome/Edge trovato. Modifica CHROME_CANDIDATES.")


# --- Utility ------------------------------------------------------------------
def slugify(text: str, maxlen: int = 60) -> str:
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen] or "pagina"


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    host = re.sub(r"^www\.", "", host)
    return slugify(host, 40)


def url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_manifest() -> dict:
    if MANIFEST_JSON.exists():
        return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    return {}


def save_manifest(entries: dict) -> None:
    MANIFEST_JSON.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fields = [
        "url", "titolo", "testata", "data_articolo",
        "data_archiviazione", "file_pdf", "hash", "stato",
    ]
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in entries.values():
            w.writerow({k: e.get(k, "") for k in fields})


def log_error(msg: str) -> None:
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}  {msg}\n")


# --- Core ---------------------------------------------------------------------
def archive_url(chrome: str, url: str, meta: dict, force: bool, entries: dict) -> str:
    h = url_hash(url)
    if h in entries and entries[h].get("stato") == "ok" and not force:
        return "skip"

    testata = meta.get("testata") or domain_of(url)
    data_art = meta.get("data_articolo") or ""
    date_part = data_art or now_iso()
    slug = slugify(urlparse(url).path or testata)
    fname = f"{slugify(testata,30)}_{date_part}_{slug}_{h}.pdf"
    out = PDF_DIR / fname

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=15000",
        f"--print-to-pdf={out}",
        url,
    ]
    try:
        subprocess.run(cmd, timeout=90, capture_output=True)
    except subprocess.TimeoutExpired:
        log_error(f"TIMEOUT {url}")
        entries[h] = _entry(url, meta, testata, data_art, "", h, "timeout")
        return "err"

    if not out.exists() or out.stat().st_size == 0:
        log_error(f"PDF vuoto/mancante {url}")
        entries[h] = _entry(url, meta, testata, data_art, "", h, "errore")
        return "err"

    entries[h] = _entry(
        url, meta, testata, data_art, f"pdf/{fname}", h, "ok"
    )
    return "ok"


def _entry(url, meta, testata, data_art, file_pdf, h, stato) -> dict:
    return {
        "url": url,
        "titolo": meta.get("titolo", ""),
        "testata": testata,
        "data_articolo": data_art,
        "data_archiviazione": now_iso(),
        "file_pdf": file_pdf,
        "hash": h,
        "stato": stato,
    }


# --- Input --------------------------------------------------------------------
def read_txt(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append({"url": line})
    return out


def read_csv(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("url", "").strip():
                out.append({k: (v or "").strip() for k, v in row.items()})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Archivia risorse web in PDF locali.")
    ap.add_argument("urls", nargs="*", help="URL da archiviare")
    ap.add_argument("--input", type=Path, help="file .txt con un URL per riga")
    ap.add_argument("--csv", type=Path, help="CSV con colonna 'url' (+ titolo/testata/data_articolo)")
    ap.add_argument("--force", action="store_true", help="rigenera anche i PDF gia' presenti")
    args = ap.parse_args()

    items: list[dict] = []
    if args.input:
        items += read_txt(args.input)
    if args.csv:
        items += read_csv(args.csv)
    items += [{"url": u} for u in args.urls]

    if not items:
        ap.error("Nessun URL fornito (usa argomenti, --input o --csv).")

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    entries = load_manifest()

    stats = {"ok": 0, "skip": 0, "err": 0}
    for i, it in enumerate(items, 1):
        url = it["url"]
        print(f"[{i}/{len(items)}] {url}", flush=True)
        res = archive_url(chrome, url, it, args.force, entries)
        stats[res] += 1
        save_manifest(entries)  # salva progressivo (ripartenza sicura)

    print(f"\nFatto. Nuovi: {stats['ok']}  Saltati: {stats['skip']}  Errori: {stats['err']}")
    print(f"Manifest: {MANIFEST_CSV}")
    if stats["err"]:
        print(f"Errori loggati in: {ERROR_LOG}")


if __name__ == "__main__":
    main()
