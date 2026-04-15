# Slate

A minimal presentation toolkit for HTML decks.

Slate decks are single HTML files. You don't build one from scratch — you hand a template to an LLM, tell it your topic, and it adapts it.

**The workflow:**

1. **Start** ([`/start`](./start.html)) — download the Slate template.
2. **LLM** — give the template + a one-line instruction to Claude, Cowork, ChatGPT, whatever. It returns a modified HTML file.
3. **Viewer** ([`/`](./index.html)) — drop the file on the dropzone to present with keyboard nav, fullscreen, and print-to-PDF.

That's it. Three steps. No install, no config, no infrastructure.

Plus two optional power-user pieces:

- **Frame skill** (`skill/`) — a Claude Code skill that retrofits the viewer's nav/print chrome into any existing HTML deck so it works standalone.
- **MCP server** (`mcp/`) — a local MCP server for teams who want one-command deck generation from Claude Desktop / Claude Code.

No framework. No build step. Just HTML.

## Why

Decks are either locked into proprietary editors (Keynote, Google Slides, PowerPoint) or scattered across heavyweight web frameworks (reveal.js, Slides.com). Slate is for the case where you want:

- A deck that lives in a Git repo, versioned like code
- A deck that's a single shareable link or file
- A deck that prints to a proper PDF without fighting the browser
- A deck that stays out of the way during a live pitch

The frame is ~12 KB of vanilla CSS + JS. It does one thing well.

## The Viewer

Open the deployed URL (or `index.html` locally) and drop any deck file onto it. Or pass a path as a URL parameter:

```
/            → dropzone
/?deck=example/deck.html            → loads the reference deck
/?deck=example/deck.html#slide-7    → deep-links to slide 7
/example/deck.html                  → raw deck, viewable on its own
```

The viewer parses the deck's HTML, extracts every `<section class="slide">` element, and supplies the chrome on top.

Features:
- **Auto-hiding nav**: prev/next/counter pill, bottom-right, fades out after 2.4s idle
- **Hover the counter**: reveals keyboard shortcuts
- **Fullscreen** (`F`): true presentation mode — each slide fills the viewport
- **Keyboard nav**: `←` `→` `↑` `↓` `Space` `PageUp` `PageDown` `Home` `End`
- **URL anchors**: `#slide-5` deep-links to slide 5; URL updates as you navigate
- **Print to PDF** (`P`): one slide per page with backgrounds and colors preserved
- **Recent decks**: localStorage list of decks loaded by URL
- **Drag & drop**: any `.html` file onto the dropzone

For `?deck=` URL loading to work, the files need to be served over HTTP (a deployed Vercel / Netlify / GitHub Pages build, or `python3 -m http.server` locally). Browsers block `fetch()` across `file://` paths, so local opens only support drag-and-drop and the file picker — not `?deck=` URLs.

## The Frame Skill

For Claude Code users. If you already have an HTML deck and want the viewer's frame baked in so the file is self-contained, use the `slate-frame` skill.

**Install:**
```bash
cp -r skill ~/.claude/skills/slate-frame
```

**Use** (from Claude Code):
> "Slate-frame this deck: `./my-deck.html`"

The skill injects a single grep-able block:

```html
<!-- slate-frame:start v1 -->
<style>…</style>
<nav class="dfnav">…</nav>
<script>…</script>
<!-- slate-frame:end -->
```

before `</body>`. Re-running updates the block in place. Deletion is a two-marker find-and-delete. All classes are namespaced `.dfnav-*` so the frame won't collide with the deck's own styles.

## The Design System

The `example/` folder contains a reference 12-slide deck built on the Slate aesthetic:

| # | Type | Background |
|---|------|------------|
| 01 | Title | Gradient / dark |
| 02 | Agenda | Light |
| 03 | Statement | Gradient / dark |
| 04 | Two-column context | Light |
| 05 | Narrative | Light |
| 06 | Stats | Light |
| 07 | Principles | Dark |
| 08 | Methodology | Light |
| 09 | Quote | Light |
| 10 | Case study | Light |
| 11 | Deliverables | Light |
| 12 | Close | Gradient / dark |

Non-negotiables:
- **Typography**: Inter only. Weights 400/500/600/700. Tight letter-spacing on headlines, loose tracking on eyebrows.
- **Sizing**: `cqw` (container query width) units, not `px`. Every text size is proportional to the slide width.
- **Chrome**: Every slide has the same bottom-left mark + page counter. Consistency sells the system.
- **Rule lines**: Hairline (0.6px) horizontal rules as dividers, not boxes or borders.

## How decks need to be structured

Slate expects each slide as a top-level `<section>` with the class `slide`:

```html
<!DOCTYPE html>
<html>
<head>
  <title>My Deck</title>
  <style>
    /* your design system */
    .slide { aspect-ratio: 16/9; … }
  </style>
</head>
<body>
  <main class="gallery">
    <section class="slide">Slide 1 content</section>
    <section class="slide">Slide 2 content</section>
    <section class="slide">Slide 3 content</section>
  </main>
</body>
</html>
```

That's the only contract. Layout everything inside each `<section>` however you like — Slate won't touch it.

## How to use (template workflow)

**The easy way: use the start page.** Open [`/start`](./start.html), download the template, give it to your LLM with the provided instruction, save the response, open it in the viewer.

**The template is `/template.html`** — a complete, working 12-slide deck with placeholder copy in every slide type. The LLM's only job is to swap copy inside the existing `<section class="slide">` blocks, not rebuild the design.

### The instruction to give the LLM

```
Adapt this Slate template to create a deck about [YOUR TOPIC].
Audience: [WHO THE DECK IS FOR].
Accent colour: [HEX, e.g. #3D3FB7].

Keep all CSS, class names, and HTML structure exactly as-is.
Only replace the placeholder copy inside each <section class="slide">.
Update the <title> tag and the "STUDIO" wordmark in each slide's chrome.
Return the complete modified HTML as a single code block.
```

That's the whole prompt you ever need. No other guardrails, no design system explanations — the template enforces the design system by existing.

### If you'd rather prompt from scratch

If you want the LLM to build a deck *without* the template (different aspect ratio, different slide types, whatever), the design system reference is below. Most of the time you shouldn't need this — the template is more reliable.

````
You are creating an HTML presentation deck for Slate
(https://github.com/Highamm-coder/Slate).

TOPIC: [what the deck is about — one or two sentences]
BRAND / WORDMARK: [your name or studio, shown in the chrome]
ACCENT COLOR (hex): [e.g. #3D3FB7]
SLIDE COUNT: [e.g. 12]
CONTENT: [paste your copy here, OR write: "generate placeholder copy on the topic above"]

STRUCTURE
- Output a single self-contained HTML file (no external files, no build step).
- Every slide is a top-level <section class="slide"> inside <main class="gallery">.
- 16:9 aspect ratio per slide: aspect-ratio: 16/9; container-type: inline-size.
- No navigation, no keyboard handlers, no print styles — Slate's viewer adds those.

TYPOGRAPHY
- Inter only, loaded from Google Fonts. Weights 400, 500, 600, 700.
- Sizes in cqw (container query width) so slides scale proportionally.
- Headlines: 600 weight, letter-spacing -0.022em, line-height 1.02–1.10.
- Eyebrows / small labels: 500 weight, letter-spacing 0.22em, UPPERCASE.
- Body: 400 weight, line-height 1.55, color muted (not pure black).
- Use <em> for emphasis, styled as non-italic, 500 weight, in the accent color.

COLOR
- Light slides: white (#FFFFFF) background, dark ink (~#121332).
- Dark slides: a darkened version of the accent (~15% luminance) as background,
  off-white ink (~#F2F1EC). Alternate light and dark slides for rhythm.
- Hairline dividers only (0.6px rules). No cards, no thick borders, no shadows
  on text, no decorative gradients.

CHROME (applied to every slide)
- Top meta row: uppercase eyebrow on the left (accent color), section label on
  the right (faint ink), hairline rule below.
- Bottom chrome: accent-colored dot + brand wordmark on the left, page number
  "NN / TOTAL" on the right. Both in very small uppercase letter-spaced type.

SLIDE TYPES (pick a mix that fits the content; don't use all if unnecessary)
1.  Title — bold headline, short subtitle, 3-column meta strip (prepared by /
    for / date). Often on a dark or gradient-style background.
2.  Agenda — 2×2 grid of numbered sections with title + one-line description.
3.  Statement — single large pull-quote on a dark slide.
4.  Two-column context — side-by-side headings + paragraphs.
5.  Narrative — two columns of dense body copy with small subheads. Use for
    context-heavy slides.
6.  Stats — three big numbers with labels + short descriptions.
7.  Principles — three indexed rows on dark: "P · 01", title, description.
8.  Methodology — up to five numbered stages, each with step label + title +
    body paragraph.
9.  Quote — large pull-quote in the ink color with attribution line.
10. Case study — narrative column + three inline proof stats.
11. Deliverables — 2×3 grid of numbered items with title + description.
12. Close — big headline + short body + a CTA pill button + contact block.
    Often on a dark background.

AVOID
- Frameworks, build tools, or npm packages.
- Navigation controls, fragment animations, or scroll-triggered reveals.
- Shadows on text, gradients as decoration, drop caps, rounded thick borders.
- Replacing Inter with another font.

OUTPUT
Return the complete HTML file as a single code block. Nothing else.
````

Save the output as `deck.html` next to `index.html` (or inside the `example/` folder), then:

- **Locally**: open `index.html`, drag `deck.html` onto the dropzone.
- **Deployed**: visit `yourslatedomain.com/?deck=deck.html`.

If you want the deck to also work standalone (without the viewer), run the `slate-frame` Claude Code skill on it — it injects the same nav/print chrome directly into the file so it's self-contained and shareable.

## How to use (with the MCP server)

For teams who want every member to have one-command deck generation without copy-pasting prompts, install the MCP server once and wire it into Claude Desktop or Claude Code.

```bash
cd mcp
pip install -e .
```

Then add to Claude Desktop's config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "slate": {
      "command": "slate-mcp"
    }
  }
}
```

Restart Claude Desktop. Any team member can now just say:

> *Make me a 10-slide Slate deck about our pricing changes, prepared for the board. Save it to my Desktop.*

Claude calls `slate_create_deck` with structured slide data, the server renders a Slate-compliant HTML file with the frame baked in, and it lands on disk. No prompt copy-paste, no manual save, and iteration works (*"tighten slide 6"*, *"swap slides 3 and 5"*) because Claude can call `slate_apply_frame` or re-run `slate_create_deck` with updated input.

See [`mcp/README.md`](./mcp/README.md) for the full tool reference, slide-type schema, and troubleshooting.

## Project structure

```
slate/
├── index.html               the viewer (served at /)
├── start.html               the "start a deck" onboarding page (served at /start)
├── template.html            the Slate template LLMs adapt
├── skill/                   optional: slate-frame Claude Code skill
│   ├── SKILL.md
│   └── assets/
│       ├── frame.css
│       ├── frame.js
│       └── frame-markup.html
├── mcp/                     optional: slate-mcp local MCP server
│   ├── pyproject.toml
│   ├── README.md
│   └── slate_mcp/
│       └── server.py
└── example/                 reference deck (branded)
    ├── deck.html
    └── assets/
```

## Credits

Built by [Deksia](https://deksia.com).
