#!/usr/bin/env python3
"""
archive_resolver.py — Trova copie archiviate (anti-paywall) di una risorsa.

Per ogni URL cerca uno snapshot esistente su:
  - Wayback Machine (web.archive.org)  — via availability API, affidabile, programmatico
  - archive.today (archive.ph/.is)     — via TimeMap; spesso bypassa i paywall

Restituisce/segna SEMPRE entrambi i riferimenti (anche il solo link di lookup se lo
snapshot non e' confermato), perche' le fonti devono essere completissime.

Uso come modulo:
    from archive_resolver import resolve
    info = resolve(url)  # -> dict con wayback_url, archive_today_url, ...

Uso da CLI:
    python archive_resolver.py https://sito/articolo         # singolo
    python archive_resolver.py --csv data/fonti_grezze.csv   # colonna 'url'
        -> scrive data/archivi_fonti.csv (url, wayback_url, wayback_data, archive_today_url, note)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA}

# Testate/pattern notoriamente a pagamento o con consent-wall aggressivo
PAYWALL = re.compile(r"/pay/|ilmessaggero\.it|corriere\.it|repubblica\.it|"
                     r"ilsole24ore\.com|lastampa\.it|ilmattino\.it", re.I)


def is_paywalled(url: str) -> bool:
    return bool(PAYWALL.search(url))


def wayback(url: str) -> tuple[str, str]:
    """(snapshot_url, data) oppure ('','')."""
    try:
        r = requests.get("https://archive.org/wayback/available?url=" + quote(url, safe=""),
                         headers=HEADERS, timeout=25)
        if r.status_code == 200:
            snap = r.json().get("archived_snapshots", {}).get("closest")
            if snap and snap.get("available"):
                return snap["url"], snap.get("timestamp", "")[:8]
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        pass
    return "", ""


def archive_today(url: str) -> str:
    """URL del piu' recente snapshot su archive.today, se ottenibile via TimeMap.
    In caso di blocco Cloudflare restituisce comunque il link di lookup (da provare a mano/Chrome)."""
    lookup = "https://archive.ph/newest/" + url
    for base in ("https://archive.ph", "https://archive.is", "https://archive.today"):
        try:
            r = requests.get(f"{base}/timemap/{url}", headers=HEADERS, timeout=20)
            if r.status_code == 200 and "memento" in r.text.lower():
                # ultima URL http(s)://archive.* nel timemap
                mementos = re.findall(r"<(https?://archive\.[^>]+)>", r.text)
                if mementos:
                    return mementos[-1]
        except requests.RequestException:
            continue
        time.sleep(1)
    return lookup  # non confermato: link di lookup


def resolve(url: str) -> dict:
    wb_url, wb_date = wayback(url)
    at_url = archive_today(url)
    at_confermato = "/newest/" not in at_url  # se non e' il link di lookup, e' uno snapshot reale
    return {
        "url": url,
        "paywall": "si" if is_paywalled(url) else "",
        "wayback_url": wb_url,
        "wayback_data": wb_date,
        "archive_today_url": at_url,
        "archive_today_confermato": "si" if at_confermato else "",
        "note": "" if (wb_url or at_confermato) else "nessuno snapshot confermato: da creare",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--csv", type=Path, help="CSV con colonna 'url'")
    ap.add_argument("--only-paywall", action="store_true",
                    help="risolvi solo gli URL riconosciuti come paywall")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "archivi_fonti.csv")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.csv:
        with args.csv.open(encoding="utf-8-sig", newline="") as f:
            urls += [r["url"].strip() for r in csv.DictReader(f) if r.get("url", "").strip()]
    if args.only_paywall:
        urls = [u for u in urls if is_paywalled(u)]
    if not urls:
        ap.error("Nessun URL (usa argomenti o --csv).")

    fields = ["url", "paywall", "wayback_url", "wayback_data",
              "archive_today_url", "archive_today_confermato", "note"]
    rows = []
    for i, u in enumerate(urls, 1):
        info = resolve(u)
        rows.append(info)
        tag = "PAY" if info["paywall"] else "   "
        print(f"[{i}/{len(urls)}] {tag} wb:{'Y' if info['wayback_url'] else '-'} {u[:70]}", flush=True)
        time.sleep(0.6)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    npay = sum(1 for r in rows if r["paywall"])
    nwb = sum(1 for r in rows if r["wayback_url"])
    print(f"\nRisolti {len(rows)} URL · paywall {npay} · con snapshot Wayback {nwb} -> {args.out}")


if __name__ == "__main__":
    main()
