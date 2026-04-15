"""
Slate MCP Server
================

Exposes three tools to any MCP-aware client (Claude Desktop, Claude Code, etc.):

    slate_create_deck         Generate a Slate-compatible HTML deck on disk.
    slate_apply_frame         Inject the Slate nav/print frame into an existing deck.
    slate_list_slide_types    Return the schema for each supported slide type
                              so the calling LLM knows how to construct input.

Team members install once:

    pip install -e /path/to/Slate/mcp

Add to ~/Library/Application Support/Claude/claude_desktop_config.json:

    {
      "mcpServers": {
        "slate": { "command": "slate-mcp" }
      }
    }

Restart Claude Desktop. Ask Claude: "Make me a 10-slide Slate deck about X."
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("slate")

# Resolve the skill/assets directory that ships with the repo — the frame CSS
# and JS live there so a single source of truth is used by both the skill and
# the MCP server. If the MCP package is installed from a repo clone, this
# resolves to <repo>/skill/assets/. If installed standalone, users can set
# SLATE_SKILL_DIR to point elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SKILL_ASSETS = _REPO_ROOT / "skill" / "assets"


def _frame_assets_dir() -> Path:
    import os
    override = os.environ.get("SLATE_SKILL_DIR")
    if override:
        return Path(override)
    return _DEFAULT_SKILL_ASSETS


# ---------------------------------------------------------------------------
# Slide type schemas — exposed to clients via slate_list_slide_types().
# Each schema documents the fields a caller must/can provide for that type.
# ---------------------------------------------------------------------------
SLIDE_TYPES: dict[str, dict[str, Any]] = {
    "title": {
        "description": "Opening slide. Often on a dark / accent-coloured background.",
        "fields": {
            "eyebrow": "Short uppercase label above the headline (e.g. 'PRESENTATION · 2026')",
            "headline": "Main headline — short, confident, 1-2 lines. Use <em>word</em> for accent emphasis.",
            "subtitle": "Optional one-sentence subtitle below the headline.",
            "meta": "Optional list of [label, value] pairs shown as a 3-column strip (e.g. [['Prepared by','Your Name'], ...]).",
        },
        "dark_bg": True,
    },
    "agenda": {
        "description": "2×2 grid of numbered sections.",
        "fields": {
            "eyebrow": "Uppercase eyebrow (e.g. 'Agenda').",
            "section": "Uppercase section label shown on the right (e.g. 'Section 01').",
            "headline": "The main heading — often 'What we'll cover…' style.",
            "items": "List of [number, title, description] rows. Up to 4.",
        },
    },
    "statement": {
        "description": "Large single-sentence pull-quote, usually on a dark background.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "text": "The statement itself. One sentence, short.",
        },
        "dark_bg": True,
    },
    "two_column": {
        "description": "Two side-by-side columns of heading + paragraph.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "The slide's main headline.",
            "columns": "List of [subhead, body] pairs. Exactly 2.",
        },
    },
    "narrative": {
        "description": "Two columns of dense long-form body copy with subheads. Use for deep-context slides.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "Main headline.",
            "columns": "List of [subhead, body] pairs. Body can contain <em> for accent emphasis.",
        },
    },
    "stats": {
        "description": "Three large numbers with labels + short descriptions.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "Main headline (e.g. 'The case, in three figures.').",
            "stats": "List of [number, label, description] rows. Up to 3.",
        },
    },
    "principles": {
        "description": "Three indexed rows listing principles or tenets. Usually dark.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "Main headline.",
            "items": "List of [index_label, title, description] rows. Up to 3. Example index: 'P · 01'.",
        },
        "dark_bg": True,
    },
    "methodology": {
        "description": "Numbered stages with step label + title + body, one per row.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "Main headline.",
            "stages": "List of [step, title, body] rows. Example step: '01 · LISTEN'. Up to 5.",
        },
    },
    "quote": {
        "description": "Large pull-quote with attribution.",
        "fields": {
            "eyebrow": "Uppercase eyebrow (e.g. 'In their words').",
            "section": "Uppercase section label (right).",
            "text": "The quote itself.",
            "attribution": "Uppercase attribution (e.g. 'PARTNER NAME · HEAD OF STRATEGY · ORG').",
        },
    },
    "case_study": {
        "description": "Narrative column + three inline proof stats.",
        "fields": {
            "eyebrow": "Uppercase eyebrow.",
            "section": "Uppercase section label (right).",
            "headline": "Main headline.",
            "case_title": "Sub-heading above the narrative body.",
            "narrative": "Multi-paragraph body copy. Separate paragraphs with blank lines.",
            "proofs": "List of [number, label, description] rows. Up to 3.",
        },
    },
    "deliverables": {
        "description": "2×3 grid of numbered deliverable items.",
        "fields": {
            "eyebrow": "Uppercase eyebrow (e.g. \"What's included\").",
            "section": "Uppercase section label (right).",
            "headline": "Main headline.",
            "items": "List of [number, title, description] rows. Up to 6.",
        },
    },
    "close": {
        "description": "Closing slide. CTA button + contact block. Usually dark.",
        "fields": {
            "eyebrow": "Uppercase eyebrow (e.g. 'Next').",
            "section": "Uppercase section label (right, e.g. 'Close').",
            "headline": "Main headline.",
            "body": "Short paragraph below the headline.",
            "cta_label": "Text for the CTA button (e.g. 'Book the kickoff →').",
            "contact": "List of strings: [name, email, phone]. Any subset.",
        },
        "dark_bg": True,
    },
}


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    )


def _derive_palette(accent: str) -> dict[str, str]:
    """From a single accent hex, derive a coherent Slate palette."""
    r, g, b = _hex_to_rgb(accent)
    # Dark background: very dark version of the accent hue (~13% luminance)
    dark_bg = _rgb_to_hex(int(r * 0.19), int(g * 0.19), int(b * 0.19))
    # Soft companion: lighter tint for dark-slide emphasis (~65% white mix)
    soft = _rgb_to_hex(
        int(r + (255 - r) * 0.55),
        int(g + (255 - g) * 0.55),
        int(b + (255 - b) * 0.55),
    )
    return {
        "accent": accent.upper() if accent.startswith("#") else f"#{accent.upper()}",
        "accent_soft": soft,
        "dark_bg": dark_bg,
        "ink": "#121332",
        "ink_muted": "#585B7A",
        "ink_faint": "#9A9CB3",
        "page_bg": "#EEECE6",
        "slide_bg": "#FFFFFF",
        "rule_light": "rgba(18,19,50,0.09)",
        "rule_dark": "rgba(255,255,255,0.14)",
    }


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------
_BASE_CSS = r"""
:root{
  --page-bg:{page_bg};
  --slide-bg:{slide_bg};
  --slide-bg-dark:{dark_bg};
  --accent:{accent};
  --accent-soft:{accent_soft};
  --ink:{ink};
  --ink-muted:{ink_muted};
  --ink-faint:{ink_faint};
  --rule:{rule_light};
  --rule-dark:{rule_dark};
}
*{margin:0;padding:0;box-sizing:border-box;}
html{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
body{
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  background:var(--page-bg);
  color:var(--ink);
  padding:56px 24px 140px;
  min-height:100vh;
  font-feature-settings:"ss01","cv11";
}
.gallery{max-width:1400px;margin:0 auto;display:flex;flex-direction:column;gap:32px;}
.slide{
  position:relative;width:100%;aspect-ratio:16/9;
  background:var(--slide-bg);color:var(--ink);
  overflow:hidden;container-type:inline-size;
  box-shadow:0 1px 2px rgba(0,0,0,0.04),0 24px 60px -20px rgba(18,19,50,0.18);
  border-radius:4px;
}
.slide.dark{background:var(--slide-bg-dark);color:#F2F1EC;}
.inner{position:absolute;inset:0;padding:6cqw 7cqw;display:flex;flex-direction:column;z-index:2;}

/* --- type primitives --- */
.eyebrow{font-weight:500;font-size:.85cqw;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);}
.slide.dark .eyebrow{color:var(--accent-soft);}
.sec{font-weight:500;font-size:.78cqw;letter-spacing:.22em;text-transform:uppercase;color:var(--ink-faint);}
.slide.dark .sec{color:rgba(255,255,255,0.55);}
.h1{font-weight:600;font-size:5.4cqw;line-height:1.02;letter-spacing:-.028em;}
.h2{font-weight:600;font-size:3.4cqw;line-height:1.06;letter-spacing:-.022em;}
.h3{font-weight:500;font-size:1.4cqw;line-height:1.25;letter-spacing:-.012em;}
.body{font-weight:400;font-size:1.05cqw;line-height:1.6;color:var(--ink-muted);}
.slide.dark .body{color:rgba(242,241,236,0.72);}
em{font-style:normal;font-weight:500;color:var(--accent);}
.slide.dark em{color:var(--accent-soft);}
.mono{font-variant-numeric:tabular-nums;}

/* --- meta row --- */
.meta-row{display:flex;align-items:baseline;justify-content:space-between;
  padding-bottom:1.8cqw;border-bottom:1px solid var(--rule);margin-bottom:3.2cqw;}
.slide.dark .meta-row{border-color:var(--rule-dark);}

/* --- chrome (bottom bar) --- */
.chrome{position:absolute;left:7cqw;right:7cqw;bottom:3.2cqw;
  display:flex;align-items:center;justify-content:space-between;
  font-size:.78cqw;letter-spacing:.22em;text-transform:uppercase;color:var(--ink-faint);z-index:3;}
.slide.dark .chrome{color:rgba(255,255,255,0.42);}
.chrome .mark{display:flex;align-items:center;gap:.6cqw;}
.chrome .dot{width:.55cqw;height:.55cqw;border-radius:50%;background:var(--accent);}
.slide.dark .chrome .dot{background:var(--accent-soft);}

/* --- title slide --- */
.slide.title{background:var(--slide-bg-dark);color:#FFFFFF;}
.slide.title .inner{justify-content:space-between;}
.slide.title .eyebrow{color:rgba(255,255,255,0.85);}
.slide.title .h1 em{color:var(--accent-soft);}
.slide.title .sub{margin-top:2.2cqw;font-size:1.25cqw;color:rgba(255,255,255,0.78);font-weight:300;max-width:62%;line-height:1.5;}
.slide.title .meta{margin-top:2.4cqw;display:flex;gap:2.2cqw;font-size:.82cqw;letter-spacing:.22em;text-transform:uppercase;color:rgba(255,255,255,0.7);}
.slide.title .meta span strong{display:block;color:#FFFFFF;font-weight:500;margin-top:.35cqw;letter-spacing:.08em;text-transform:none;font-size:1.1cqw;}

/* --- agenda grid --- */
.agenda-grid{margin-top:auto;display:grid;grid-template-columns:repeat(2,1fr);gap:2.2cqw 4cqw;}
.agenda-item{display:grid;grid-template-columns:3cqw 1fr;gap:1.4cqw;padding:1.4cqw 0;border-top:1px solid var(--rule);}
.agenda-item .num{font-size:.95cqw;font-weight:500;color:var(--accent);letter-spacing:.04em;padding-top:.3cqw;}
.agenda-item .ttl{font-size:1.4cqw;font-weight:500;line-height:1.2;letter-spacing:-.012em;}
.agenda-item .sub{font-size:.95cqw;color:var(--ink-muted);margin-top:.5cqw;line-height:1.5;}

/* --- statement --- */
.statement{margin:auto 0;max-width:82%;font-size:2.6cqw;font-weight:400;line-height:1.3;letter-spacing:-.016em;color:#FFFFFF;}
.statement em{color:var(--accent-soft);font-weight:500;}

/* --- two-column / narrative --- */
.cols{margin-top:auto;display:grid;grid-template-columns:1fr 1fr;gap:4.5cqw;padding-top:2.4cqw;border-top:1px solid var(--rule);}
.cols .col h3{font-size:1.3cqw;font-weight:500;letter-spacing:-.012em;margin-bottom:1cqw;color:var(--ink);}
.cols .col p{font-size:1cqw;line-height:1.65;color:var(--ink-muted);margin-bottom:.9cqw;}
.cols .col p:last-child{margin-bottom:0;}

/* --- stats --- */
.stats{margin-top:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:3cqw;padding-top:3cqw;border-top:1px solid var(--rule);}
.stat .num{font-size:5.8cqw;font-weight:500;letter-spacing:-.03em;line-height:1;color:var(--accent);}
.stat .lbl{margin-top:.8cqw;font-size:.95cqw;font-weight:500;color:var(--ink);}
.stat .desc{margin-top:.4cqw;font-size:.9cqw;color:var(--ink-muted);line-height:1.55;}

/* --- principles list (dark) --- */
.plist{margin-top:auto;display:flex;flex-direction:column;}
.prow{display:grid;grid-template-columns:3cqw 1.3fr 1fr;gap:2.4cqw;padding:1.6cqw 0;border-bottom:1px solid var(--rule-dark);align-items:baseline;}
.prow:first-child{border-top:1px solid var(--rule-dark);}
.prow .idx{font-size:.9cqw;font-weight:500;color:var(--accent-soft);letter-spacing:.04em;}
.prow .h{font-size:1.35cqw;font-weight:500;letter-spacing:-.012em;color:#F2F1EC;}
.prow .d{font-size:1cqw;color:rgba(242,241,236,0.72);line-height:1.55;}

/* --- methodology --- */
.method{margin-top:auto;display:flex;flex-direction:column;}
.mrow{display:grid;grid-template-columns:6cqw 1fr 1.6fr;gap:2cqw;padding:1cqw 0;border-bottom:1px solid var(--rule);align-items:baseline;}
.mrow:first-child{border-top:1px solid var(--rule);}
.mrow .step{font-size:.82cqw;font-weight:500;color:var(--accent);letter-spacing:.12em;text-transform:uppercase;}
.mrow h4{font-size:1.15cqw;font-weight:500;color:var(--ink);line-height:1.25;letter-spacing:-.012em;}
.mrow p{font-size:.88cqw;line-height:1.55;color:var(--ink-muted);}

/* --- quote --- */
.quote{margin:auto 0;max-width:82%;}
.quote .mark-q{font-size:4.5cqw;font-weight:500;color:var(--accent);line-height:0;display:inline-block;transform:translateY(1.2cqw);}
.quote .q{font-size:2.4cqw;font-weight:400;line-height:1.3;letter-spacing:-.014em;}
.quote .attr{margin-top:2.2cqw;font-size:.88cqw;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-muted);}

/* --- case study --- */
.case{margin-top:auto;display:grid;grid-template-columns:1.4fr 1fr;gap:5cqw;padding-top:2.4cqw;border-top:1px solid var(--rule);align-items:start;}
.case h3{font-size:1.35cqw;font-weight:500;letter-spacing:-.012em;margin-bottom:1cqw;color:var(--ink);}
.case p{font-size:.95cqw;line-height:1.65;color:var(--ink-muted);margin-bottom:.85cqw;}
.case p:last-child{margin-bottom:0;}
.case .proofs{display:flex;flex-direction:column;}
.case .proof{padding:1.2cqw 0;border-top:1px solid var(--rule);}
.case .proof .num{font-size:3.2cqw;font-weight:500;letter-spacing:-.025em;line-height:1;color:var(--accent);}
.case .proof .lbl{margin-top:.5cqw;font-size:.85cqw;font-weight:500;color:var(--ink);}
.case .proof .desc{margin-top:.3cqw;font-size:.82cqw;color:var(--ink-muted);line-height:1.5;}

/* --- deliverables --- */
.deliver{margin-top:auto;display:grid;grid-template-columns:repeat(2,1fr);gap:1.6cqw 4cqw;padding-top:2.4cqw;border-top:1px solid var(--rule);}
.dv{display:grid;grid-template-columns:2.8cqw 1fr;gap:1cqw;padding:.8cqw 0;}
.dv .n{font-size:.88cqw;font-weight:500;color:var(--accent);letter-spacing:.04em;padding-top:.2cqw;}
.dv .t{font-size:1.1cqw;font-weight:500;letter-spacing:-.012em;color:var(--ink);margin-bottom:.35cqw;}
.dv .d{font-size:.88cqw;color:var(--ink-muted);line-height:1.55;}

/* --- close --- */
.close-layout{margin-top:auto;display:grid;grid-template-columns:1.5fr 1fr;gap:6cqw;align-items:end;}
.close-layout .cta{display:inline-flex;align-items:center;gap:1cqw;padding:1.4cqw 2cqw;background:#FFFFFF;color:var(--slide-bg-dark);border-radius:2px;font-size:1cqw;font-weight:500;text-decoration:none;}
.close-layout .contact{display:flex;flex-direction:column;gap:.5cqw;font-size:.98cqw;color:rgba(242,241,236,0.72);line-height:1.5;}
.close-layout .contact strong{color:#F2F1EC;font-weight:500;}
"""


def _escape(s: str) -> str:
    """Minimal HTML escape that preserves allowed inline tags (<em> and <br>)."""
    if s is None:
        return ""
    out = str(s)
    # Placeholder inline tags so escape() doesn't nuke them
    out = out.replace("<em>", "\x00EM\x00").replace("</em>", "\x00/EM\x00")
    out = out.replace("<br>", "\x00BR\x00").replace("<br/>", "\x00BR\x00").replace("<br />", "\x00BR\x00")
    out = (
        out.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    out = out.replace("\x00EM\x00", "<em>").replace("\x00/EM\x00", "</em>")
    out = out.replace("\x00BR\x00", "<br>")
    return out


def _paragraphs(body: str) -> str:
    """Split body copy on blank lines into <p> blocks."""
    if not body:
        return ""
    chunks = [c.strip() for c in re.split(r"\n\s*\n", body) if c.strip()]
    return "".join(f"<p>{_escape(p)}</p>" for p in chunks)


def _meta_row(eyebrow: str, section: str) -> str:
    return (
        f'<div class="meta-row">'
        f'<span class="eyebrow">{_escape(eyebrow or "")}</span>'
        f'<span class="sec">{_escape(section or "")}</span>'
        f"</div>"
    )


def _chrome(brand: str, page_num: int, total: int) -> str:
    return (
        f'<div class="chrome">'
        f'<div class="mark"><span class="dot"></span><span>{_escape(brand)}</span></div>'
        f"<span>{page_num:02d} / {total:02d}</span>"
        f"</div>"
    )


def _render_slide(slide: dict, idx: int, total: int, brand: str) -> str:
    stype = slide.get("type", "").lower().strip()
    schema = SLIDE_TYPES.get(stype)
    if not schema:
        raise ValueError(f"Unknown slide type on slide {idx + 1}: '{stype}'")

    page_num = idx + 1
    dark = schema.get("dark_bg", False)
    cls = f"slide{' dark' if dark else ''}"
    if stype == "title":
        cls += " title"

    inner_content = ""

    if stype == "title":
        eb = _escape(slide.get("eyebrow", ""))
        headline = _escape(slide.get("headline", ""))
        sub = _escape(slide.get("subtitle", ""))
        meta_items = slide.get("meta") or []
        meta_html = ""
        if meta_items:
            meta_html = '<div class="meta">' + "".join(
                f'<span>{_escape(lbl)}<strong>{_escape(val)}</strong></span>'
                for lbl, val in meta_items
            ) + "</div>"
        inner_content = (
            f'<div class="eyebrow">{eb}</div>'
            f'<div class="title-block" style="margin-top:auto;">'
            f'<h1 class="h1">{headline}</h1>'
            + (f'<p class="sub">{sub}</p>' if sub else "")
            + meta_html
            + "</div>"
        )

    elif stype == "agenda":
        items = slide.get("items") or []
        item_html = ""
        for num, ttl, desc in items[:4]:
            item_html += (
                f'<div class="agenda-item">'
                f'<div class="num">{_escape(num)}</div>'
                f'<div><div class="ttl">{_escape(ttl)}</div>'
                f'<div class="sub">{_escape(desc)}</div></div>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:78%;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="agenda-grid">{item_html}</div>'
        )

    elif stype == "statement":
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<div class="statement">{_escape(slide.get("text",""))}</div>'
        )

    elif stype in ("two_column", "narrative"):
        cols = slide.get("columns") or []
        col_html = ""
        for sub, body in cols[:2]:
            col_html += (
                f'<div class="col">'
                f'<h3>{_escape(sub)}</h3>'
                f"{_paragraphs(body)}"
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:70%;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="cols">{col_html}</div>'
        )

    elif stype == "stats":
        stats = slide.get("stats") or []
        stats_html = ""
        for num, lbl, desc in stats[:3]:
            stats_html += (
                f'<div class="stat">'
                f'<div class="num mono">{_escape(num)}</div>'
                f'<div class="lbl">{_escape(lbl)}</div>'
                f'<div class="desc">{_escape(desc)}</div>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:60%;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="stats">{stats_html}</div>'
        )

    elif stype == "principles":
        items = slide.get("items") or []
        rows = ""
        for idx_label, h, d in items[:3]:
            rows += (
                f'<div class="prow">'
                f'<div class="idx">{_escape(idx_label)}</div>'
                f'<div class="h">{_escape(h)}</div>'
                f'<div class="d">{_escape(d)}</div>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:70%;color:#F2F1EC;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="plist">{rows}</div>'
        )

    elif stype == "methodology":
        stages = slide.get("stages") or []
        rows = ""
        for step, t, body in stages[:5]:
            rows += (
                f'<div class="mrow">'
                f'<div class="step">{_escape(step)}</div>'
                f'<h4>{_escape(t)}</h4>'
                f'<p>{_escape(body)}</p>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:72%;font-size:2.6cqw;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="method">{rows}</div>'
        )

    elif stype == "quote":
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<div class="quote">'
            f'<span class="mark-q">“</span>'
            f'<p class="q">{_escape(slide.get("text",""))}</p>'
            f'<p class="attr">{_escape(slide.get("attribution",""))}</p>'
            f"</div>"
        )

    elif stype == "case_study":
        proofs = slide.get("proofs") or []
        proof_html = ""
        for num, lbl, desc in proofs[:3]:
            proof_html += (
                f'<div class="proof">'
                f'<div class="num mono">{_escape(num)}</div>'
                f'<div class="lbl">{_escape(lbl)}</div>'
                f'<div class="desc">{_escape(desc)}</div>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:72%;font-size:2.6cqw;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="case">'
            + f'<div class="narr"><h3>{_escape(slide.get("case_title",""))}</h3>{_paragraphs(slide.get("narrative",""))}</div>'
            + f'<div class="proofs">{proof_html}</div>'
            + "</div>"
        )

    elif stype == "deliverables":
        items = slide.get("items") or []
        item_html = ""
        for num, t, d in items[:6]:
            item_html += (
                f'<div class="dv">'
                f'<div class="n">{_escape(num)}</div>'
                f'<div><div class="t">{_escape(t)}</div>'
                f'<div class="d">{_escape(d)}</div></div>'
                f"</div>"
            )
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:72%;font-size:2.6cqw;">{_escape(slide.get("headline",""))}</h2>'
            + f'<div class="deliver">{item_html}</div>'
        )

    elif stype == "close":
        contact = slide.get("contact") or []
        contact_html = ""
        if contact:
            if len(contact) >= 1:
                contact_html += f'<strong>{_escape(contact[0])}</strong>'
            for c in contact[1:]:
                contact_html += f'<span>{_escape(c)}</span>'
        inner_content = (
            _meta_row(slide.get("eyebrow", ""), slide.get("section", ""))
            + f'<h2 class="h2" style="max-width:78%;color:#FFFFFF;">{_escape(slide.get("headline",""))}</h2>'
            + (f'<p class="body" style="max-width:60%;margin-top:1.4cqw;color:rgba(242,241,236,0.78);">{_escape(slide.get("body",""))}</p>' if slide.get("body") else "")
            + '<div class="close-layout">'
            + f'<a href="#" class="cta">{_escape(slide.get("cta_label","Next step →"))}</a>'
            + f'<div class="contact">{contact_html}</div>'
            + "</div>"
        )

    return (
        f'<section class="{cls}">'
        f'<div class="inner">{inner_content}</div>'
        f"{_chrome(brand, page_num, total)}"
        f"</section>"
    )


def _render_deck_html(
    deck_title: str, brand: str, accent_hex: str, slides: list[dict]
) -> str:
    palette = _derive_palette(accent_hex)
    css = _BASE_CSS.format(**palette)
    total = len(slides)
    slide_html = "\n".join(
        _render_slide(s, i, total, brand) for i, s in enumerate(slides)
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{_escape(deck_title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<main class="gallery">
{slide_html}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Frame injection (mirrors the slate-frame skill's behaviour)
# ---------------------------------------------------------------------------
FRAME_START = "<!-- slate-frame:start v1 -->"
FRAME_END = "<!-- slate-frame:end -->"


def _load_frame_block() -> str:
    assets = _frame_assets_dir()
    css = (assets / "frame.css").read_text()
    markup = (assets / "frame-markup.html").read_text()
    js = (assets / "frame.js").read_text()
    return (
        f"{FRAME_START}\n"
        f"<style>{css}</style>\n"
        f"{markup}\n"
        f"<script>{js}</script>\n"
        f"{FRAME_END}\n"
    )


def _inject_frame(html: str) -> str:
    """Insert (or replace) the slate-frame block just before </body>."""
    block = _load_frame_block()
    existing = re.search(
        re.escape(FRAME_START) + r".*?" + re.escape(FRAME_END) + r"\n?",
        html,
        re.DOTALL,
    )
    if existing:
        return html[: existing.start()] + block + html[existing.end() :]
    # Insert before </body>
    if "</body>" in html:
        return html.replace("</body>", block + "</body>", 1)
    # No </body>? Append at end.
    return html + "\n" + block


# ---------------------------------------------------------------------------
# MCP tool declarations
# ---------------------------------------------------------------------------
@mcp.tool()
def slate_create_deck(
    output_path: str,
    deck_title: str,
    brand: str,
    accent_hex: str = "#3D3FB7",
    slides: list[dict] | None = None,
    include_frame: bool = True,
) -> str:
    """Generate a Slate-compatible HTML deck and write it to output_path.

    Args:
        output_path: Absolute or relative path where the deck should be written
            (e.g. "~/Desktop/pitch.html"). Parent directories must exist.
        deck_title: Shown in the browser tab and viewer topbar.
        brand: The wordmark rendered in each slide's bottom chrome (e.g. "DEKSIA").
        accent_hex: Single hex colour driving the whole palette (buttons,
            eyebrows, accent emphasis). Defaults to "#3D3FB7" (Slate indigo).
        slides: Ordered list of slide dicts. Call slate_list_slide_types() first
            to see the schema for each type. Minimum one slide.
        include_frame: When True (default), bakes the slate-frame nav/print
            chrome into the file so it works standalone without the viewer.

    Returns:
        A short status message with the resolved absolute path.
    """
    if not slides:
        raise ValueError("slides list is required and must not be empty")

    html = _render_deck_html(deck_title, brand, accent_hex, slides)
    if include_frame:
        html = _inject_frame(html)

    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
    return f"Wrote {len(slides)}-slide deck to {path}"


@mcp.tool()
def slate_apply_frame(deck_path: str) -> str:
    """Inject the Slate nav/print frame into an existing HTML deck.

    Use this when a user has hand-authored or previously generated a deck
    without the frame and now wants keyboard nav, URL anchors, and print-to-PDF
    support baked in. Safe to re-run; updates an existing frame block in place.

    Args:
        deck_path: Path to an HTML file containing <section class="slide">
            elements.

    Returns:
        A status message describing whether the frame was newly injected or
        updated.
    """
    path = Path(deck_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No such deck: {path}")
    html = path.read_text()
    had_frame = FRAME_START in html
    new_html = _inject_frame(html)
    path.write_text(new_html)
    return (
        f"{'Updated' if had_frame else 'Injected'} slate-frame in {path}"
    )


@mcp.tool()
def slate_list_slide_types() -> str:
    """Return the schema for every supported slide type as JSON.

    Call this before slate_create_deck so you know what fields each slide type
    accepts. The schema includes a description of each type, its fields, and
    whether it renders on a dark background by default.
    """
    return json.dumps(SLIDE_TYPES, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
