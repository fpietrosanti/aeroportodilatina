#!/usr/bin/env python3
"""
build_site.py — Genera il sito statico (HTML) dalla fonte unica del dossier.

Statico puro (nessun Jekyll): output nella root del repo, servibile da GitHub
Pages (branch main, cartella / root). Rigenerabile: NON modificare gli .html a mano.

Output:
    index.html            — landing
    cronistoria.html      — timeline eventi (link esterno + copia PDF)
    stakeholder.html      — mappa favorevoli/contrari/ambivalenti
    da-reperire.html      — documenti offline da acquisire
    .nojekyll             — disattiva l'elaborazione Jekyll
"""
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANIFEST = ROOT / "archive" / "manifest.json"

CSS = """
:root{--blu:#0b3d67;--blu2:#12557f;--bg:#f7f8fa;--card:#fff;--bordo:#e3e7ec;
--verde:#1d8a4c;--rosso:#b3261e;--giallo:#b8860b;--arancio:#c2570c;--txt:#1a2230;--muted:#5a6675}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
color:var(--txt);background:var(--bg);line-height:1.55}
a{color:var(--blu2);text-decoration:none}a:hover{text-decoration:underline}
header.site{background:linear-gradient(135deg,var(--blu),var(--blu2));color:#fff;padding:2.4rem 1.2rem}
header.site .wrap{max-width:900px;margin:0 auto}
header.site h1{margin:0 0 .3rem;font-size:1.9rem}
header.site p{margin:.2rem 0 0;opacity:.92}
nav.top{max-width:900px;margin:1rem auto 0;padding:0 1.2rem;display:flex;gap:1.2rem;flex-wrap:wrap}
nav.top a{color:#dff}
main{max-width:900px;margin:0 auto;padding:1.6rem 1.2rem 3rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem;margin:1.4rem 0}
.card{background:var(--card);border:1px solid var(--bordo);border-radius:10px;padding:1.1rem 1.2rem}
.card h3{margin:.1rem 0 .4rem}.card p{margin:.2rem 0;color:var(--muted);font-size:.94rem}
.event{background:var(--card);border:1px solid var(--bordo);border-left:4px solid var(--blu2);
border-radius:8px;padding:1rem 1.2rem;margin:1rem 0}
.event.off{border-left-color:var(--rosso)}
.event.inst{border-left-color:#7b5cd6;background:#faf9ff}
.badge-inst{display:inline-block;font-size:.7rem;font-weight:700;padding:.15rem .5rem;border-radius:4px;background:#7b5cd6;color:#fff;vertical-align:middle}
.event h2{margin:.1rem 0 .5rem;font-size:1.12rem}
.event .id{font:600 .72rem/1 monospace;color:var(--muted);background:#eef2f6;padding:.2rem .4rem;border-radius:4px}
.meta{font-size:.85rem;color:var(--muted);margin:.3rem 0}
.badge{display:inline-block;font-size:.72rem;font-weight:600;padding:.15rem .5rem;border-radius:999px;color:#fff}
.b-fav{background:var(--verde)}.b-con{background:var(--rosso)}.b-neu{background:var(--giallo)}.b-amb{background:var(--arancio)}
.quote{border-left:3px solid var(--bordo);margin:.5rem 0;padding:.2rem .8rem;color:#374050;font-style:italic}
.fonti{font-size:.9rem;margin-top:.4rem}.fonti .pdf{font-weight:600}
.reperire{background:#fff6f5;border:1px solid #f2d0cc;border-radius:6px;padding:.5rem .8rem;margin-top:.5rem;font-size:.88rem}
.group{margin:1.6rem 0 .6rem;font-size:1.2rem}
.rass{padding:.35rem 0;border-bottom:1px solid var(--bordo);font-size:.95rem}
.rass .id{color:var(--muted);font-family:monospace;font-size:.8rem;margin-right:.3rem}
footer{max-width:900px;margin:0 auto;padding:1.5rem 1.2rem 3rem;color:var(--muted);font-size:.82rem;border-top:1px solid var(--bordo)}
.disclaimer{background:#fffbe6;border:1px solid #f0e4a8;border-radius:6px;padding:.7rem .9rem;font-size:.85rem;margin-top:1rem}
"""

BADGE = {"FAVOREVOLE": "b-fav", "CONTRARIO": "b-con",
         "NEUTRO-CONDIZIONATO": "b-neu", "AMBIVALENTE-MUTEVOLE": "b-amb"}

# Domini di enti pubblici -> fonte istituzionale (da evidenziare)
INST_DOMAINS = ("senato.it", "camera.it", "regione.lazio.it", "comune.latina.it",
                "provincia.latina.it", "enac.gov.it", "gazzettaufficiale.it",
                "governo.it", "mit.gov.it", "pianomobilitalazio.it", "parlamento.it")


def is_institutional(fonti) -> bool:
    for s in fonti or []:
        u = (s.get("url") or "").lower()
        if any(d in u for d in INST_DOMAINS) or "istituzional" in (s.get("quality") or ""):
            return True
    return False


def e(s) -> str:
    return html.escape(str(s or ""))


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def pdf_map() -> dict:
    if not MANIFEST.exists():
        return {}
    m = load(MANIFEST)
    return {v["url"]: "archive/" + v["file_pdf"]
            for v in m.values() if v.get("stato") == "ok" and v.get("file_pdf")}


def page(title: str, body: str) -> str:
    nav = ('<nav class="top"><a href="index.html">Home</a>'
           '<a href="cronistoria.html">Cronistoria</a>'
           '<a href="atti.html">Atti</a>'
           '<a href="rassegna-stampa.html">Rassegna stampa</a>'
           '<a href="stakeholder.html">Stakeholder</a>'
           '<a href="da-reperire.html">Da reperire</a></nav>')
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — Comitato per l'Aeroporto di Latina</title><style>{CSS}</style></head>
<body><header class="site"><div class="wrap"><h1>Comitato per l'Aeroporto di Latina</h1>
<p>Archivio documentale delle vicende dell'aeroporto "Enrico Comani" e delle proposte di uso civile</p></div>
{nav}</header><main>{body}</main>
<footer><div class="disclaimer">Le copie PDF sono conservate a fini di documentazione e
consultazione storica; i diritti restano dei rispettivi editori. Segnalazioni:
apri una issue sul <a href="https://github.com/fpietrosanti/aeroportodilatina">repository</a>.</div>
<p>Base dati aperta · fonte di verità: <code>data/*.json</code> · pagine generate automaticamente.</p></footer>
</body></html>"""


def build_index(cron, stake, atti=None) -> str:
    n = len(cron["eventi"])
    off = sum(1 for x in cron["eventi"] if x["stato_reperimento"] == "OFFLINE-DA-REPERIRE")
    fav = sum(1 for x in stake["stakeholder"] if x["posizione"] == "FAVOREVOLE")
    con = sum(1 for x in stake["stakeholder"] if x["posizione"] == "CONTRARIO")
    n_atti = len(atti["atti"]) if atti else 0
    card_atti = (f'<div class="card"><h3><a href="atti.html">📑 Registro atti</a></h3>'
                 f'<p>{n_atti} atti istituzionali (mozioni, interrogazioni, ordini del giorno) '
                 f'citati dagli articoli, con lo stato dell\'originale.</p></div>') if atti else ""
    body = f"""<p>{e(cron['meta']['descrizione'])}</p>
<div class="cards">
<div class="card"><h3><a href="cronistoria.html">📜 Cronistoria</a></h3>
<p>{n} eventi verificati, dal 1938 al 2026, con fonti e copie PDF archiviate.</p></div>
{card_atti}
<div class="card"><h3><a href="stakeholder.html">👥 Mappa stakeholder</a></h3>
<p>{len(stake['stakeholder'])} soggetti: {fav} favorevoli, {con} contrari, e posizioni ambivalenti.</p></div>
<div class="card"><h3><a href="da-reperire.html">🗂️ Documenti da reperire</a></h3>
<p>{off} documenti noti ma non ancora acquisiti, con ente detentore e modalità di richiesta.</p></div>
</div>
<h2>Metodo</h2>
<p>Ogni affermazione è ancorata a una fonte verificabile e, dove possibile, a una copia
PDF archiviata localmente. L'analisi rinvia sempre alla cronistoria tramite ID stabili
(es. <code>EV-2018-001</code>). Le lacune documentali sono esplicitate.</p>"""
    return page("Home", body)


def build_cronistoria(cron, pm) -> str:
    rows = []
    for x in cron["eventi"]:
        off = x["stato_reperimento"] == "OFFLINE-DA-REPERIRE"
        inst = is_institutional(x.get("fonti"))
        fonti = []
        for s in x.get("fonti", []):
            if not s.get("url"):
                continue
            link = f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s.get("testata","fonte"))}</a>'
            if pm.get(s["url"]):
                link += f' <a class="pdf" href="{e(pm[s["url"]])}" target="_blank">📄 PDF</a>'
            fonti.append(link)
        fonti_html = f'<div class="fonti"><strong>Fonti:</strong> {" · ".join(fonti)}</div>' if fonti else ""
        quote = f'<div class="quote">«{e(x["estratto"])}»</div>' if x.get("estratto") else ""
        rep = ""
        if off:
            rep = (f'<div class="reperire">🔴 <strong>Da reperire</strong> — '
                   f'{e(x.get("ente_detentore",""))}<br><em>{e(x.get("modalita_richiesta",""))}</em></div>')
        sog = f'<div class="meta"><strong>Soggetti:</strong> {e(" · ".join(x.get("soggetti",[])))}</div>' if x.get("soggetti") else ""
        cls = "event" + (" off" if off else "") + (" inst" if inst else "")
        inst_badge = ' <span class="badge-inst">🏛️ FONTE ISTITUZIONALE</span>' if inst else ""
        rows.append(f"""<article class="{cls}">
<h2>{e(x['titolo_evento'])} <span class="id">{e(x['id'])}</span>{inst_badge}</h2>
<div class="meta">📅 {e(x['data'])} · {e(x['categoria_evento'])} · esito: {e(x['esito'])} · affidabilità: {e(x['affidabilita'])}</div>
{sog}<p>{e(x['descrizione'])}</p>{quote}{fonti_html}{rep}</article>""")
    body = f"<h1>Cronistoria</h1><p class='meta'>{len(cron['eventi'])} eventi · ultimo aggiornamento {e(cron['meta']['ultimo_aggiornamento'])}</p>" + "".join(rows)
    return page("Cronistoria", body)


def build_stakeholder(stake) -> str:
    order = ["FAVOREVOLE", "CONTRARIO", "NEUTRO-CONDIZIONATO", "AMBIVALENTE-MUTEVOLE"]
    label = {"FAVOREVOLE": "🟢 Favorevoli", "CONTRARIO": "🔴 Contrari",
             "NEUTRO-CONDIZIONATO": "🟡 Neutri/condizionati", "AMBIVALENTE-MUTEVOLE": "🟠 Ambivalenti/mutevoli"}
    out = ["<h1>Mappa degli stakeholder</h1>"]
    for pos in order:
        grp = [s for s in stake["stakeholder"] if s["posizione"] == pos]
        if not grp:
            continue
        out.append(f'<h2 class="group">{label[pos]} ({len(grp)})</h2>')
        for s in grp:
            part = f", {e(s['partito'])}" if s.get("partito") else ""
            out.append(f"""<article class="event">
<h2>{e(s['soggetto'])} <span class="badge {BADGE[pos]}">{e(pos)}</span></h2>
<div class="meta">{e(s['ruolo'])}{part} · {e(s['ente'])} · <em>{e(s['periodo'])}</em></div>
<p>{e(s['motivazione'])}</p>
<div class="meta">↳ eventi: {e(", ".join(s.get('eventi',[])))}</div></article>""")
    return page("Stakeholder", "".join(out))


def build_atti(atti, pm) -> str:
    lst = atti["atti"]
    def keyf(a):
        return (a.get("data") or "9999")
    lst = sorted(lst, key=keyf)
    trovati = sum(1 for a in lst if a["stato_originale"] == "trovato")
    out = [f"<h1>Registro degli atti istituzionali</h1>",
           f"<p class='meta'>{len(lst)} atti · originali reperiti: {trovati} · "
           f"da reperire: {len(lst)-trovati}</p>",
           f"<p>{e(atti['meta']['descrizione'])}</p>"]
    for a in lst:
        found = a["stato_originale"] == "trovato"
        badge = ('<span class="badge b-fav">ORIGINALE TROVATO</span>' if found
                 else '<span class="badge b-con">DA REPERIRE OFFLINE</span>')
        cls = "event" + ("" if found else " off")
        # articoli fonte
        fonti = ""
        if a.get("articoli_fonte"):
            links = " · ".join(f'<a href="{e(u)}" target="_blank" rel="noopener">fonte</a>'
                               for u in a["articoli_fonte"])
            fonti = f'<div class="fonti"><strong>Articoli che lo citano ({len(a["articoli_fonte"])}):</strong> {links}</div>'
        # originale o reperimento
        if found:
            orig = f'<div class="fonti"><strong>Originale:</strong> '
            if a.get("originale_url"):
                orig += f'<a href="{e(a["originale_url"])}" target="_blank">atto</a> '
            if a.get("pdf_locale"):
                orig += f'<a class="pdf" href="archive/{e(a["pdf_locale"])}" target="_blank">📄 PDF</a>'
            orig += "</div>"
        else:
            orig = (f'<div class="reperire">🔴 <strong>Da reperire</strong> — '
                    f'{e(a.get("ente_detentore",""))}<br><em>{e(a.get("modalita_richiesta",""))}</em></div>')
        ev = f' · <a href="cronistoria.html">{e(a["evento_collegato"])}</a>' if a.get("evento_collegato") else ""
        num = f' · {e(a["numero_atto"])}' if a.get("numero_atto") else ""
        esito = f' · esito: {e(a["esito"])}' if a.get("esito") else ""
        out.append(f"""<article class="{cls}">
<h2>{e(a['atto_tipo'])} — {e(a['oggetto'])} {badge}</h2>
<div class="meta">📅 {e(a['data'])}{num}{esito} · <strong>{e(a['ente_sede'])}</strong>{ev}</div>
<div class="meta"><strong>Promotore:</strong> {e(a['promotore'])} ({e(a['ruolo_partito'])})</div>
{fonti}{orig}</article>""")
    return page("Atti", "".join(out))


def _data_articolo(url, riga):
    if riga.get("data"):
        return riga["data"][:10]
    m = re.search(r"/(20\d\d)/(\d\d)/(\d\d)/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"/(20\d\d)/(\d\d)/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"-(20\d\d)\.html", url) or re.search(r"(20\d\d)", url)
    return m.group(1) if m else ""


def build_rassegna(pm) -> str:
    src = DATA / "fonti_triage.csv"
    if not src.exists():
        return page("Rassegna stampa", "<h1>Rassegna stampa</h1><p>Corpus non ancora generato.</p>")
    core = [r for r in csv.DictReader(src.open(encoding="utf-8-sig"))
            if r.get("categoria") == "core"]
    for r in core:
        r["_data"] = _data_articolo(r["url"], r)
    # raggruppa per testata
    testate = {}
    for r in core:
        testate.setdefault(r.get("testata") or "—", []).append(r)
    n_pdf = sum(1 for r in core if pm.get(r["url"]))
    out = [f"<h1>Rassegna stampa</h1>",
           f"<p class='meta'>{len(core)} articoli sul tema (categoria core) · "
           f"{n_pdf} con copia PDF archiviata · {len(testate)} testate</p>",
           "<p>Corpus completo degli articoli sul filone dell'aeroporto civile di Latina. "
           "Il raggruppamento per argomento (fonte principale + fonti che riprendono lo "
           "stesso fatto) è nelle pagine <a href='atti.html'>Atti</a> e "
           "<a href='cronistoria.html'>Cronistoria</a>.</p>"]
    for testata in sorted(testate, key=lambda t: -len(testate[t])):
        arts = sorted(testate[testata], key=lambda r: r["_data"] or "0", reverse=True)
        out.append(f'<h2 class="group">{e(testata)} <span class="meta">({len(arts)})</span></h2>')
        for r in arts:
            pdf = pm.get(r["url"])
            pdflink = f' · <a class="pdf" href="{e(pdf)}" target="_blank">📄 PDF</a>' if pdf else ""
            data = f'<span class="id">{e(r["_data"])}</span> ' if r["_data"] else ""
            titolo = e(r.get("titolo") or r["url"])[:160]
            out.append(f'<div class="rass">{data}<a href="{e(r["url"])}" target="_blank" '
                       f'rel="noopener">{titolo}</a>{pdflink}</div>')
    return page("Rassegna stampa", "".join(out))


BASE_URL = "https://aeroportolatina.it"


def build_sitemap(lastmod):
    """sitemap.xml con le pagine HTML e i PDF archiviati (rigenerata a ogni build)."""
    pages = [("", "1.0"), ("cronistoria.html", "0.9"), ("atti.html", "0.9"),
             ("rassegna-stampa.html", "0.8"), ("stakeholder.html", "0.7"),
             ("da-reperire.html", "0.6")]
    entries = [(f"{BASE_URL}/{p}", lastmod, prio) for p, prio in pages]
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for v in sorted(m.values(), key=lambda x: x.get("file_pdf", "")):
            if v.get("stato") == "ok" and v.get("file_pdf"):
                d = (v.get("data_archiviazione") or lastmod)[:10]
                entries.append((f"{BASE_URL}/archive/{v['file_pdf']}", d, "0.4"))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod, prio in entries:
        out.append(f"  <url><loc>{e(loc)}</loc>"
                   f"<lastmod>{e(mod)}</lastmod><priority>{prio}</priority></url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n", len(entries)


def build_da_reperire(cron) -> str:
    off = [x for x in cron["eventi"] if x["stato_reperimento"] == "OFFLINE-DA-REPERIRE"]
    out = [f"<h1>Documenti da reperire</h1><p class='meta'>{len(off)} voci offline · piano di acquisizione</p>"]
    for x in off:
        out.append(f"""<article class="event off">
<h2>{e(x['titolo_evento'])} <span class="id">{e(x['id'])}</span></h2>
<div class="meta">📅 {e(x['data'])}</div>
<p><strong>Ente detentore:</strong> {e(x.get('ente_detentore',''))}</p>
<p><strong>Modalità di richiesta:</strong> {e(x.get('modalita_richiesta',''))}</p>
<p class="meta">{e(x.get('note_reperimento',''))}</p></article>""")
    return page("Da reperire", "".join(out))


def main() -> None:
    cron = load(DATA / "cronistoria.json")
    stake = load(DATA / "stakeholder.json")
    atti = load(DATA / "atti.json") if (DATA / "atti.json").exists() else None
    pm = pdf_map()
    (ROOT / "index.html").write_text(build_index(cron, stake, atti), encoding="utf-8")
    (ROOT / "cronistoria.html").write_text(build_cronistoria(cron, pm), encoding="utf-8")
    (ROOT / "stakeholder.html").write_text(build_stakeholder(stake), encoding="utf-8")
    (ROOT / "da-reperire.html").write_text(build_da_reperire(cron), encoding="utf-8")
    if atti:
        (ROOT / "atti.html").write_text(build_atti(atti, pm), encoding="utf-8")
    (ROOT / "rassegna-stampa.html").write_text(build_rassegna(pm), encoding="utf-8")
    lastmod = cron["meta"].get("ultimo_aggiornamento", "")
    sitemap, n_url = build_sitemap(lastmod)
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Sito generato: index, cronistoria, atti, rassegna-stampa, stakeholder, "
          f"da-reperire, sitemap.xml ({n_url} url), robots.txt (+ .nojekyll)")


if __name__ == "__main__":
    main()
