#!/usr/bin/env python3
"""
build_brand.py — Genera il brand kit: sorgenti SVG + PNG social esportati (Chrome headless).

Output:
  brand/logo/     favicon.svg, emblem.svg, avatar.svg, horizontal.svg, mono.svg
  brand/social/   PNG pronti per Facebook / Telegram / LinkedIn (dimensioni esatte)
Rigenerabile: rilancia lo script per riprodurre tutto.
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "brand" / "logo"
SOCIAL = ROOT / "brand" / "social"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# --- Palette ---
BLU = "#0b3d67"
BLU2 = "#12557f"
GOLD = "#f0b429"
GOLD2 = "#e0a300"
IVORY = "#f4f6f8"
SKY = "#4f7ba6"
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

# Arte del marchio (torre + rondine + traiettoria), trasparente, viewBox 0 0 120 120
MARK = f"""
<line x1="30" y1="88" x2="90" y2="88" stroke="{SKY}" stroke-width="2.5" stroke-linecap="round"/>
<rect x="53" y="42" width="14" height="46" fill="{IVORY}"/>
<rect x="50" y="35" width="20" height="7" rx="1" fill="{IVORY}"/>
<line x1="53" y1="52" x2="67" y2="52" stroke="{BLU}" stroke-width="1.6"/>
<line x1="53" y1="60" x2="67" y2="60" stroke="{BLU}" stroke-width="1.6"/>
<line x1="53" y1="68" x2="67" y2="68" stroke="{BLU}" stroke-width="1.6"/>
<line x1="53" y1="76" x2="67" y2="76" stroke="{BLU}" stroke-width="1.6"/>
<path d="M60 84 Q70 58 88 42" fill="none" stroke="{GOLD}" stroke-width="2" stroke-dasharray="1.5 3.5" stroke-linecap="round"/>
<path d="M76 48 Q82 41 88 46 Q94 39 100 44" fill="none" stroke="{GOLD}" stroke-width="2.8" stroke-linecap="round"/>
"""

MARK_MONO = MARK.replace(IVORY, "#ffffff").replace(BLU, "#ffffff").replace(SKY, "#ffffff").replace(GOLD, "#ffffff")


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    sys.exit("Chrome non trovato")


def svg_emblem(size=120):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" '
            f'width="{size}" height="{size}" role="img" aria-label="Comitato per l\'Aeroporto di Latina">'
            f'<circle cx="60" cy="60" r="58" fill="{BLU}"/>{MARK}</svg>')


def svg_avatar():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" '
            f'aria-label="Comitato per l\'Aeroporto di Latina">'
            f'<rect width="120" height="120" fill="{BLU}"/>'
            f'<g transform="translate(8 8) scale(0.87)">{MARK}</g></svg>')


def svg_horizontal():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 140" role="img" '
            f'aria-label="Comitato per l\'Aeroporto di Latina">'
            f'<g transform="translate(6 10)"><circle cx="60" cy="60" r="58" fill="{BLU}"/>{MARK}</g>'
            f'<text x="150" y="62" font-family="{FONT}" font-size="30" font-weight="600" fill="{BLU}">Comitato per l\'Aeroporto</text>'
            f'<text x="150" y="98" font-family="{FONT}" font-size="30" font-weight="600" fill="{BLU}">di Latina</text>'
            f'<text x="150" y="126" font-family="{FONT}" font-size="17" fill="{GOLD2}">Per il terzo scalo del Lazio</text></svg>')


def svg_favicon():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
            f'<rect width="120" height="120" rx="24" fill="{BLU}"/>'
            f'<g transform="translate(6 6) scale(0.9)">{MARK}</g></svg>')


def svg_mono():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="logo monocromatico">'
            f'<circle cx="60" cy="60" r="58" fill="none" stroke="#ffffff" stroke-width="2"/>{MARK_MONO}</svg>')


# --- Composizioni social (HTML -> PNG) ---
def html_square(px):
    inner = f'<svg width="{int(px*0.78)}" height="{int(px*0.78)}" viewBox="0 0 120 120">{MARK}</svg>'
    return (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}'
            f'.c{{width:{px}px;height:{px}px;background:{BLU};display:flex;align-items:center;justify-content:center}}</style>'
            f'<div class="c">{inner}</div>')


def html_banner(w, h, title_px, sub_px, badge):
    emblem = f'<svg width="{badge}" height="{badge}" viewBox="0 0 120 120"><circle cx="60" cy="60" r="58" fill="{BLU2}"/>{MARK}</svg>'
    return (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}'
            f'.c{{width:{w}px;height:{h}px;background:{BLU};display:flex;align-items:center;'
            f'padding:0 {int(h*0.22)}px;gap:{int(h*0.14)}px;box-sizing:border-box;font-family:{FONT}}}'
            f'.t{{color:#fff;font-weight:600;font-size:{title_px}px;line-height:1.12;letter-spacing:.3px}}'
            f'.s{{color:{GOLD};font-size:{sub_px}px;margin-top:6px}}</style>'
            f'<div class="c">{emblem}<div><div class="t">Comitato per l\'Aeroporto di Latina</div>'
            f'<div class="s">Per il terzo scalo del Lazio &middot; aeroportolatina.it</div></div></div>')


def html_cover(w, h, mark_px, title_px, sub_px):
    emblem = f'<svg width="{mark_px}" height="{mark_px}" viewBox="0 0 120 120"><circle cx="60" cy="60" r="58" fill="{BLU2}"/>{MARK}</svg>'
    return (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}'
            f'.c{{width:{w}px;height:{h}px;background:{BLU};display:flex;flex-direction:column;'
            f'align-items:center;justify-content:center;gap:{int(h*0.03)}px;font-family:{FONT}}}'
            f'.t{{color:#fff;font-weight:600;font-size:{title_px}px;letter-spacing:.4px}}'
            f'.s{{color:{GOLD};font-size:{sub_px}px}}</style>'
            f'<div class="c">{emblem}<div class="t">Comitato per l\'Aeroporto di Latina</div>'
            f'<div class="s">Per il terzo scalo del Lazio &middot; aeroportolatina.it</div></div>')


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[12:16] == b"IHDR":
        return struct.unpack(">II", head[16:24])
    return (0, 0)


def render(chrome, html, out, w, h):
    tmp = out.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", f"--window-size={w},{h}",
           "--default-background-color=00000000", f"--screenshot={out}", str(tmp)]
    subprocess.run(cmd, timeout=60, capture_output=True)
    tmp.unlink(missing_ok=True)
    gw, gh = png_size(out)
    ok = "OK" if (gw, gh) == (w, h) else f"ATTESO {w}x{h}"
    print(f"  {out.name:42} {gw}x{gh}  {ok}")


def main():
    LOGO.mkdir(parents=True, exist_ok=True)
    SOCIAL.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()

    print("SVG sorgenti:")
    (LOGO / "favicon.svg").write_text(svg_favicon(), encoding="utf-8")
    (LOGO / "emblem.svg").write_text(svg_emblem(), encoding="utf-8")
    (LOGO / "avatar.svg").write_text(svg_avatar(), encoding="utf-8")
    (LOGO / "horizontal.svg").write_text(svg_horizontal(), encoding="utf-8")
    (LOGO / "mono.svg").write_text(svg_mono(), encoding="utf-8")
    for f in sorted(LOGO.glob("*.svg")):
        print(f"  {f.name}")

    print("PNG social:")
    # Telegram: avatar canale (quadrato, min 512)
    render(chrome, html_square(512), SOCIAL / "telegram-channel-avatar-512.png", 512, 512)
    render(chrome, html_square(1024), SOCIAL / "avatar-1024.png", 1024, 1024)
    # LinkedIn: logo pagina (quadrato) + cover
    render(chrome, html_square(400), SOCIAL / "linkedin-logo-400.png", 400, 400)
    render(chrome, html_banner(1128, 191, 30, 15, 130),
           SOCIAL / "linkedin-cover-1128x191.png", 1128, 191)
    # Facebook: icona quadrata + cover gruppo
    render(chrome, html_square(500), SOCIAL / "facebook-icon-500.png", 500, 500)
    render(chrome, html_cover(1640, 856, 300, 58, 30),
           SOCIAL / "facebook-group-cover-1640x856.png", 1640, 856)

    print("Fatto.")


if __name__ == "__main__":
    main()
