# Brand kit — Comitato per l'Aeroporto di Latina

Identità visiva del progetto. Tutti gli asset sono **rigenerabili**:
`python tools/build_brand.py` ricrea gli SVG sorgente e le PNG social.

## Logo

Concept **"Torre e volo"**: la torre civica razionalista di Latina (città di
fondazione) che spicca il volo — una rondine dorata sale lungo la traiettoria.
Unisce identità cittadina e aspirazione aeroportuale.

Varianti in `brand/logo/`:
| File | Uso |
|---|---|
| `emblem.svg` | emblema circolare, sfondo trasparente — uso generale |
| `avatar.svg` | quadrato a fondo pieno blu — avatar social (crop a cerchio) |
| `horizontal.svg` | lockup orizzontale con wordmark — intestazioni, carta |
| `mono.svg` | monocromatico bianco — su fondi scuri/foto |
| `favicon.svg` | icona arrotondata — favicon del sito |

## Colori

| Ruolo | HEX | Note |
|---|---|---|
| Blu istituzionale | `#0b3d67` | colore primario, sfondi |
| Blu medio | `#12557f` | badge, elementi secondari |
| Oro grano | `#f0b429` | accento (volo, evidenza) |
| Oro scuro | `#e0a300` | testo accento su chiaro |
| Avorio | `#f4f6f8` | superfici chiare, torre |
| Azzurro cielo | `#4f7ba6` | dettagli, linea terra |

## Tipografia

- Wordmark e social: **Segoe UI / Helvetica Neue / Arial** (sans, peso 600 per il
  nome, 400 per il tagline).
- Sito web: system sans (già impostato).
- Tagline ufficiale: **"Per il terzo scalo del Lazio"**.

## Regole d'uso

- Mantieni un'area di rispetto attorno al logo pari almeno al raggio della torre.
- Non deformare, non ruotare, non cambiare i colori del marchio.
- Su fondo scuro/foto usa `mono.svg` (bianco) o l'avatar a fondo pieno.
- Sentence case: "Comitato per l'Aeroporto di Latina" — mai tutto maiuscolo.

## Asset social (già esportati in PNG) — `brand/social/`

| File | Piattaforma | Dimensioni |
|---|---|---|
| `telegram-channel-avatar-512.png` | **Telegram** — foto canale | 512×512 |
| `linkedin-logo-400.png` | **LinkedIn** — logo pagina | 400×400 |
| `linkedin-cover-1128x191.png` | **LinkedIn** — immagine di copertina | 1128×191 |
| `facebook-icon-500.png` | **Facebook** — icona gruppo/pagina | 500×500 |
| `facebook-group-cover-1640x856.png` | **Facebook** — copertina gruppo | 1640×856 |
| `avatar-1024.png` | uso generale (avatar ad alta risoluzione) | 1024×1024 |

Le PNG sono pronte al caricamento diretto. Gli avatar sono a fondo pieno perché le
piattaforme li ritagliano a cerchio.
