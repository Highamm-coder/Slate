# Slate

A minimal presentation toolkit for HTML decks.

Slate is three things that work together:

1. **Viewer** (`viewer.html`) — a standalone web app that loads any HTML deck and adds keyboard navigation, fullscreen presentation mode, URL anchor deep-linking, and print-to-PDF.
2. **Frame skill** (`skill/`) — a Claude Code skill that injects the same frame directly into any existing HTML deck file, so it becomes self-contained.
3. **Design system** (`example/`) — a reference deck showing the typography, color tokens, and 12 slide layouts the toolkit is built around.

No framework. No build step. Just HTML.

## Why

Decks are either locked into proprietary editors (Keynote, Google Slides, PowerPoint) or scattered across heavyweight web frameworks (reveal.js, Slides.com). Slate is for the case where you want:

- A deck that lives in a Git repo, versioned like code
- A deck that's a single shareable link or file
- A deck that prints to a proper PDF without fighting the browser
- A deck that stays out of the way during a live pitch

The frame is ~12 KB of vanilla CSS + JS. It does one thing well.

## The Viewer

Open `viewer.html` and drop any deck file onto it. Or pass a path as a URL parameter:

```
viewer.html?deck=./example/deck.html
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

For `?deck=` URL loading to work, serve the folder over HTTP:

```bash
python3 -m http.server
# then open http://localhost:8000/viewer.html?deck=./example/deck.html
```

(Local `file://` loading works via drag-and-drop or the file picker, but browsers block `fetch()` across local files.)

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
  <main>
    <section class="slide">Slide 1 content</section>
    <section class="slide">Slide 2 content</section>
    <section class="slide">Slide 3 content</section>
  </main>
</body>
</html>
```

That's the only contract. Layout everything inside each `<section>` however you like — Slate won't touch it.

## Project structure

```
slate/
├── viewer.html              the viewer web app
├── skill/                   the slate-frame Claude Code skill
│   ├── SKILL.md
│   └── assets/
│       ├── frame.css
│       ├── frame.js
│       └── frame-markup.html
└── example/                 reference deck
    ├── deck.html
    └── assets/              gradient images + logo
```

## Credits

Built by [Deksia](https://deksia.com).
