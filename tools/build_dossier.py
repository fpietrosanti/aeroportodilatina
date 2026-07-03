#!/usr/bin/env python3
"""
build_dossier.py — Genera le viste derivate dalla fonte unica del dossier.

Input (fonte di verita'):
    data/cronistoria.json
    data/stakeholder.json

Output (rigenerabili, NON modificare a mano):
    data/cronistoria.csv          — timeline tabellare (una riga per evento)
    data/cronistoria.md           — timeline leggibile
    data/stakeholder.csv          — mappa stakeholder tabellare
    data/stakeholder.md           — mappa stakeholder leggibile (favorevoli/contrari/...)
    data/fonti_da_archiviare.csv  — URL unici da dare a archive_sources.py
    data/da_reperire.md           — elenco documenti OFFLINE con ente e modalita'
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MANIFEST = ROOT / "archive" / "manifest.json"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_pdf_map() -> dict:
    """url -> percorso PDF archiviato (relativo alla cartella data/)."""
    if not MANIFEST.exists():
        return {}
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = {}
    for e in m.values():
        if e.get("stato") == "ok" and e.get("file_pdf"):
            out[e["url"]] = "../archive/" + e["file_pdf"]
    return out


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def join(vals) -> str:
    return " | ".join(vals) if isinstance(vals, list) else (vals or "")


def fonti_str(fonti: list[dict]) -> str:
    out = []
    for s in fonti:
        bits = [b for b in [s.get("testata"), s.get("data"), s.get("url")] if b]
        out.append(" ".join(bits))
    return " ; ".join(out)


def build_cronistoria() -> None:
    doc = load("cronistoria.json")
    eventi = doc["eventi"]
    pdf_map = load_pdf_map()

    # CSV
    fields = [
        "id", "data", "data_precisione", "titolo_evento", "categoria_evento",
        "tema", "esito", "affidabilita", "soggetti", "estratto",
        "stato_reperimento", "ente_detentore", "modalita_richiesta", "fonti",
    ]
    rows = []
    for e in eventi:
        rows.append({
            **e,
            "tema": join(e.get("tema", [])),
            "soggetti": join(e.get("soggetti", [])),
            "fonti": fonti_str(e.get("fonti", [])),
        })
    write_csv(DATA / "cronistoria.csv", fields, rows)

    # Markdown
    lines = [
        f"# {doc['meta']['titolo']}", "",
        f"> {doc['meta']['descrizione']}", "",
        f"*Ultimo aggiornamento: {doc['meta']['ultimo_aggiornamento']}. "
        f"{len(eventi)} voci. Fonte di verita': `cronistoria.json` (non modificare i .md/.csv generati).*",
        "",
    ]
    for e in eventi:
        flag = "🔴 DA REPERIRE" if e["stato_reperimento"] == "OFFLINE-DA-REPERIRE" else ""
        lines += [
            f"## {e['data']} — {e['titolo_evento']}  `{e['id']}` {flag}".rstrip(),
            "",
            f"- **Categoria:** {e['categoria_evento']}  ·  **Tema:** {join(e.get('tema', []))}  ·  "
            f"**Esito:** {e['esito']}  ·  **Affidabilità:** {e['affidabilita']}",
        ]
        if e.get("soggetti"):
            lines.append(f"- **Soggetti:** {join(e['soggetti'])}")
        lines.append(f"- **Descrizione:** {e['descrizione']}")
        if e.get("estratto"):
            lines.append(f"- **Citazione:** «{e['estratto']}»")
        # Fonti con link esterno + copia PDF locale archiviata
        if e.get("fonti"):
            parts = []
            for s in e["fonti"]:
                if not s.get("url"):
                    continue
                link = f"[{s.get('testata','fonte')}]({s['url']})"
                pdf = pdf_map.get(s["url"])
                if pdf:
                    link += f" ([📄 copia PDF]({pdf}))"
                parts.append(link)
            lines.append(f"- **Fonti:** {'; '.join(parts)}")
        if e["stato_reperimento"] == "OFFLINE-DA-REPERIRE":
            lines.append(
                f"- **⚠ Reperimento:** {e.get('ente_detentore','')} — "
                f"_{e.get('modalita_richiesta','')}_"
            )
        lines.append("")
    (DATA / "cronistoria.md").write_text("\n".join(lines), encoding="utf-8")

    # Fonti da archiviare (URL unici)
    seen = {}
    for e in eventi:
        for s in e.get("fonti", []):
            u = s.get("url", "").strip()
            if u and u not in seen:
                seen[u] = {
                    "url": u,
                    "titolo": e["titolo_evento"],
                    "testata": s.get("testata", ""),
                    "data_articolo": s.get("data", ""),
                }
    write_csv(
        DATA / "fonti_da_archiviare.csv",
        ["url", "titolo", "testata", "data_articolo"],
        list(seen.values()),
    )

    # Da reperire
    off = [e for e in eventi if e["stato_reperimento"] == "OFFLINE-DA-REPERIRE"]
    dl = ["# Documenti/atti da reperire (offline)", "",
          f"*{len(off)} voci con stato OFFLINE-DA-REPERIRE.*", ""]
    for e in off:
        dl += [
            f"## {e['id']} — {e['titolo_evento']} ({e['data']})",
            f"- **Ente detentore:** {e.get('ente_detentore','')}",
            f"- **Modalità di richiesta:** {e.get('modalita_richiesta','')}",
            f"- **Note:** {e.get('note_reperimento','')}",
            "",
        ]
    (DATA / "da_reperire.md").write_text("\n".join(dl), encoding="utf-8")

    return len(eventi), len(seen), len(off)


def build_stakeholder() -> None:
    doc = load("stakeholder.json")
    sh = doc["stakeholder"]

    fields = ["soggetto", "ruolo", "ente", "categoria", "partito",
              "posizione", "motivazione", "periodo", "eventi"]
    rows = [{**s, "eventi": join(s.get("eventi", []))} for s in sh]
    write_csv(DATA / "stakeholder.csv", fields, rows)

    order = ["FAVOREVOLE", "CONTRARIO", "NEUTRO-CONDIZIONATO", "AMBIVALENTE-MUTEVOLE"]
    emoji = {"FAVOREVOLE": "🟢", "CONTRARIO": "🔴",
             "NEUTRO-CONDIZIONATO": "🟡", "AMBIVALENTE-MUTEVOLE": "🟠"}
    lines = [f"# {doc['meta']['titolo']}", "", f"> {doc['meta']['descrizione']}", ""]
    for pos in order:
        grp = [s for s in sh if s["posizione"] == pos]
        if not grp:
            continue
        lines += [f"## {emoji.get(pos,'')} {pos} ({len(grp)})", ""]
        for s in grp:
            ev = ", ".join(s.get("eventi", []))
            lines.append(
                f"- **{s['soggetto']}** — {s['ruolo']}"
                + (f", {s['partito']}" if s.get("partito") else "")
                + f" · _{s['periodo']}_  \n  {s['motivazione']}  \n  ↳ eventi: {ev}"
            )
        lines.append("")
    (DATA / "stakeholder.md").write_text("\n".join(lines), encoding="utf-8")
    return len(sh)


def main() -> None:
    n_ev, n_src, n_off = build_cronistoria()
    n_sh = build_stakeholder()
    print(f"Cronistoria: {n_ev} eventi  ·  {n_src} fonti uniche  ·  {n_off} da reperire")
    print(f"Stakeholder: {n_sh} soggetti")
    print(f"Output in: {DATA}")


if __name__ == "__main__":
    main()
