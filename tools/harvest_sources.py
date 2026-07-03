#!/usr/bin/env python3
"""
harvest_sources.py — Rastrellamento esaustivo degli articoli sull'Aeroporto di Latina.

Tre reti combinate (DuckDuckGo risulta bloccato con 202, non usato):
  1. Ricerca interna ?s=  (testate che la supportano: WordPress + latinaoggi + ilcaffe)
  2. Pagine TAG Citynews  (latinatoday.it/tag/<termine>/ con paginazione)
  3. Google News RSS       (query multiple, resa alta, non bloccato)

Output: data/fonti_grezze.csv  (url, testata, titolo, data, query_origine, metodo)
Deduplica per URL normalizzato. Logga il conteggio per rete/testata (nessun taglio silenzioso).

Uso:
    python harvest_sources.py --probe     # test rapido
    python harvest_sources.py             # completo
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fonti_grezze.csv"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"}

# Testate con ricerca interna ?s=
SEARCHABLE = {
    "latinaoggi.eu": "https://www.latinaoggi.eu",
    "ilcaffe.tv": "https://ilcaffe.tv",
    "h24notizie.com": "https://www.h24notizie.com",
    "ilfaroonline.it": "https://www.ilfaroonline.it",
    "latinaquotidiano.it": "https://www.latinaquotidiano.it",
    "latinacorriere.it": "https://www.latinacorriere.it",
    "news-24.it": "https://news-24.it",
    "radioluna.it": "https://www.radioluna.it",
    "latinapress.it": "https://www.latinapress.it",
}

# Testate Citynews (pagine tag)
CITYNEWS = {"latinatoday.it": "https://www.latinatoday.it"}

SEARCH_TERMS = ["aeroporto", "Comani"]
TAG_TERMS = ["aeroporto"]
GNEWS_QUERIES = [
    "aeroporto Latina Comani", "aeroporto civile Latina",
    "terzo aeroporto Lazio Latina", "aeroporto militare Latina scalo",
    "Comani aeroporto civile", "aeroporto Latina low cost",
]

SKIP = re.compile(r"/(tag|category|categoria|author|autore|pagina|cerca|search|"
                  r"feed|wp-|about|contatti|privacy|cookie|redazione|gallery)/", re.I)


def get(url, method="get", data=None, tries=3):
    for i in range(tries):
        try:
            r = (requests.post(url, data=data, headers=HEADERS, timeout=25)
                 if method == "post" else
                 requests.get(url, headers=HEADERS, timeout=25))
            if r.status_code == 200:
                return r.text
            if r.status_code in (403, 429, 202):
                time.sleep(3 + i * 3)
        except requests.RequestException:
            time.sleep(2 + i * 2)
    return None


def norm(url: str) -> str:
    p = urlparse(url)
    return f"{p.netloc.lower().replace('www.', '')}{p.path.rstrip('/')}"


def article_like(url: str, domain: str) -> bool:
    p = urlparse(url)
    if domain not in p.netloc:
        return False
    if SKIP.search(p.path):
        return False
    return len(p.path.strip("/")) > 15


def add(found, key, rec):
    if key not in found:
        found[key] = rec
        return 1
    return 0


def collect_anchors(html, base, domain, meta, found):
    soup = BeautifulSoup(html, "lxml")
    hits = 0
    for a in soup.select("h1 a, h2 a, h3 a, a[rel=bookmark], article a"):
        href = a.get("href", "")
        if not href:
            continue
        href = urljoin(base, href)
        if article_like(href, domain):
            hits += add(found, norm(href), {
                "url": href, "testata": domain, "data": "",
                "titolo": a.get_text(strip=True)[:200], **meta})
    return hits


def search_s(domain, base, term, maxpages, found):
    n0 = len(found)
    for pg in range(1, maxpages + 1):
        url = f"{base}/?s={quote_plus(term)}" if pg == 1 else f"{base}/page/{pg}/?s={quote_plus(term)}"
        htm = get(url)
        if not htm:
            break
        if collect_anchors(htm, base, domain, {"query_origine": f"?s={term}", "metodo": "search"}, found) == 0:
            break
        time.sleep(1.2)
    return len(found) - n0


def search_tag(domain, base, tag, maxpages, found):
    n0 = len(found)
    for pg in range(1, maxpages + 1):
        url = f"{base}/tag/{tag}/" if pg == 1 else f"{base}/tag/{tag}/{pg}/"
        htm = get(url)
        if not htm:
            break
        if collect_anchors(htm, base, domain, {"query_origine": f"tag/{tag}", "metodo": "tag"}, found) == 0:
            break
        time.sleep(1.2)
    return len(found) - n0


def search_gnews(query, found):
    n0 = len(found)
    url = ("https://news.google.com/rss/search?q=" + quote_plus(query) +
           "&hl=it&gl=IT&ceid=IT:it")
    htm = get(url)
    if not htm:
        return 0
    try:
        root = ET.fromstring(htm)
    except ET.ParseError:
        return 0
    for item in root.iter("item"):
        link = item.findtext("link") or ""
        title = item.findtext("title") or ""
        pub = item.findtext("pubDate") or ""
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        if link:
            add(found, "gn:" + norm(link), {
                "url": link, "testata": source.strip() or "GoogleNews",
                "titolo": title.strip()[:200], "data": pub[:16],
                "query_origine": f"gnews:{query}", "metodo": "gnews"})
    return len(found) - n0


GNEWS_YEAR_QUERIES = [
    "aeroporto Latina", "aeroporto Comani Latina", "aeroporto civile Latina",
    "terzo aeroporto Lazio", "scalo Latina aeroporto",
]


def search_gnews_year(query, year, found):
    n0 = len(found)
    q = f"{query} after:{year}-01-01 before:{year}-12-31"
    url = ("https://news.google.com/rss/search?q=" + quote_plus(q) +
           "&hl=it&gl=IT&ceid=IT:it")
    htm = get(url)
    if not htm:
        return 0
    try:
        root = ET.fromstring(htm)
    except ET.ParseError:
        return 0
    for item in root.iter("item"):
        link = item.findtext("link") or ""
        title = item.findtext("title") or ""
        pub = item.findtext("pubDate") or ""
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        if link:
            add(found, "gn:" + norm(link), {
                "url": link, "testata": source.strip() or "GoogleNews",
                "titolo": title.strip()[:200], "data": pub[:16],
                "query_origine": f"gnews-anno:{year}:{query}", "metodo": "gnews-anno"})
    return len(found) - n0


def load_existing(found):
    if not OUT.exists():
        return
    with OUT.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            u = r.get("url", "").strip()
            if not u:
                continue
            key = ("gn:" + norm(u)) if r.get("metodo", "").startswith("gnews") else norm(u)
            found[key] = {k: r.get(k, "") for k in
                          ["url", "testata", "titolo", "data", "query_origine", "metodo"]}


def gnews_years(found, y_from=1995, y_to=2026):
    load_existing(found)
    print(f"Caricati {len(found)} URL esistenti. Spazzata anno per anno {y_from}-{y_to}...")
    per_year = {}
    for year in range(y_from, y_to + 1):
        c = 0
        for q in GNEWS_YEAR_QUERIES:
            c += search_gnews_year(q, year, found)
            time.sleep(1.2)
        per_year[year] = c
        print(f"  {year}: +{c} (tot {len(found)})", flush=True)
        save(found)
    print("\n=== Nuovi per anno ===")
    for y, c in per_year.items():
        bar = "#" * min(c, 40)
        print(f"  {y}: {c:3}  {bar}")
    print(f"\nTOTALE URL unici: {len(found)} -> {OUT}")


def save(found):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["url", "testata", "titolo", "data", "query_origine", "metodo"])
        w.writeheader()
        for v in found.values():
            w.writerow(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--years", action="store_true",
                    help="spazzata Google News anno per anno 1995-2026 (fonde nel CSV esistente)")
    ap.add_argument("--maxpages", type=int, default=10)
    args = ap.parse_args()

    found, per = {}, {}

    if args.years:
        gnews_years(found)
        return

    if args.probe:
        print("[probe s=] latinaoggi:", search_s("latinaoggi.eu", SEARCHABLE["latinaoggi.eu"], "aeroporto", 2, found))
        print("[probe tag] latinatoday:", search_tag("latinatoday.it", CITYNEWS["latinatoday.it"], "aeroporto", 2, found))
        print("[probe gnews]:", search_gnews("aeroporto Latina Comani", found))
        save(found)
        print("Totale probe:", len(found), "->", OUT)
        return

    for domain, base in SEARCHABLE.items():
        c = 0
        for term in SEARCH_TERMS:
            c += search_s(domain, base, term, args.maxpages, found)
        per[domain] = c
        print(f"[s=] {domain}: +{c} (tot {len(found)})", flush=True)
        save(found)

    for domain, base in CITYNEWS.items():
        c = 0
        for tag in TAG_TERMS:
            c += search_tag(domain, base, tag, args.maxpages, found)
        per[domain] = c
        print(f"[tag] {domain}: +{c} (tot {len(found)})", flush=True)
        save(found)

    cg = 0
    for q in GNEWS_QUERIES:
        cg += search_gnews(q, found)
        time.sleep(1.5)
    per["GoogleNews"] = cg
    print(f"[gnews] +{cg} (tot {len(found)})", flush=True)
    save(found)

    print("\n=== Conteggio per rete/testata ===")
    for d, n in sorted(per.items(), key=lambda x: -x[1]):
        print(f"  {d:24} {n}")
    print(f"\nTOTALE URL unici: {len(found)} -> {OUT}")


if __name__ == "__main__":
    main()
