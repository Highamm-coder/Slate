---
name: slate-frame
description: Inject the Slate navigation frame into any HTML presentation deck — keyboard arrows, click-to-advance icons, URL anchor deep-links (#slide-N), scroll-snap, hover-peek keyboard shortcuts, and a print stylesheet that produces a proper one-slide-per-page PDF with backgrounds and colors preserved. Part of the Slate deck toolkit. Use whenever the user has an existing HTML deck (or a file with `<section class="slide">` elements) and wants presenter-style navigation and PDF export added, or says things like "add Slate to this deck", "slate-frame this file", "add nav to this deck", "make this deck printable", "add arrow keys to this slide file", "wrap this with a frame", or "add the deck frame." Does not touch the deck's design, content, or existing styles — purely additive.
---

# slate-frame

The Slate frame injector. Applies the Slate presenter chrome (auto-hiding nav pill, hover-peek shortcuts, keyboard navigation, URL anchors, print-to-PDF) to any HTML deck in one step. Leaves the deck's design system completely untouched — the frame is purely additive.

Slate is the broader deck toolkit this skill belongs to — along with the Slate Viewer (a standalone web app that loads any deck HTML and supplies the same frame) and the Slate design system (the reference deck template at `/Users/matthewhigham/Documents/Ai/Roc Deck/index-indigo.html`).

Injects a single, namespaced frame block (`.dfnav-*` classes) into the target HTML. Adds:

- **Keyboard navigation**: arrows, space, PageUp/PageDown, Home/End
- **Minimal auto-hiding nav**: tiny prev/next icons + counter, fade in on mouse movement, fade out after 2.4s idle
- **Help toggle**: small `?` icon in the corner, click or press `?` to see shortcuts
- **URL anchors**: `#slide-5` deep-links to the 5th slide; URL updates as the user navigates
- **Scroll-snap**: each slide snaps into place when scrolled
- **Print to PDF**: press `P` (or Cmd-P) to print; stylesheet forces one slide per page with background colors and images preserved
- **Reveal-on-scroll**: safely adds a `.visible` class on intersection, compatible with decks that use `opacity:0` fade-ins

The frame is **purely additive** — it doesn't modify the deck's existing CSS, content, or structure. All frame classes are prefixed `dfnav-*` to avoid collisions.

## When to use this

- "Add navigation to this deck"
- "Make this deck printable to PDF"
- "Add arrow keys / keyboard shortcuts to this slide file"
- "Wrap this HTML with a deck frame"
- "Add page counter and deep-linking"

Don't trigger for:
- Single-page marketing sites (not slide-structured)
- Decks already using reveal.js / Swiper / similar frameworks (they'll conflict)
- Plain documents with no slide structure

## Prerequisites for the target file

The deck must have **slide elements with the class `.slide`**. The typical pattern:

```html
<section class="slide">…</section>
<section class="slide">…</section>
```

If the deck uses a different selector (e.g., `.page`, `.section`, `<article>`), edit the injected `frame.js` after insertion to change the `SLIDE_SELECTOR` constant. Ask the user if it's unclear.

## How to inject the frame

### 1. Gather the target file

Ask the user for the path if not provided. Confirm:
- How many `<section class="slide">` (or equivalent) elements are in the file
- Whether the frame is already injected (check for `<!-- slate-frame:start` marker)

### 2. Check for existing injection

Before inserting, grep the target file for `<!-- slate-frame:start`. If present:
- The frame is already there. Ask the user: update to latest version, or leave alone?
- **To update**: delete everything between `<!-- slate-frame:start` and `<!-- slate-frame:end -->` (inclusive), then re-insert fresh.

### 3. Read the three assets

From this skill's directory:
- `assets/frame.css` — CSS block
- `assets/frame-markup.html` — nav markup
- `assets/frame.js` — navigation script

### 4. Compose the injection block

Build a single block of the form:

```html
<!-- slate-frame:start v1 -->
<style>
/* paste full contents of frame.css here */
</style>
<!-- paste full contents of frame-markup.html here -->
<script>
/* paste full contents of frame.js here */
</script>
<!-- slate-frame:end -->
```

Keep the markers exact — later updates depend on grepping for them.

### 5. Insert before `</body>`

Use the Edit tool to insert the block immediately before the closing `</body>` tag. If the file has no `</body>` (raw HTML fragment), insert at the end of the file and add a note to the user.

**Why before `</body>` and not `</head>`:** the `<script>` needs the DOM to exist before it runs, and the nav markup needs to be in the DOM tree. Putting everything together at the end keeps the injection atomic and grep-able.

### 6. Handle edge cases

**No `.slide` elements found**: The script logs a warning and does nothing at runtime. Tell the user: "I added the frame, but the script couldn't find `.slide` elements. If your deck uses a different selector, edit line with `SLIDE_SELECTOR` in the injected script."

**Existing IDs on slides**: The script only assigns `slide-N` IDs to elements that don't already have one, so custom IDs are preserved. The URL anchor feature still works for auto-assigned IDs but custom IDs take precedence.

**Existing keyboard handlers**: If the deck has its own keydown listeners (e.g., for fragments), they might conflict. Warn the user and offer to review.

**Inter font**: The nav uses Inter and falls back to `system-ui`. If the deck doesn't include Inter, the nav looks fine in the system font. If visual consistency matters, suggest the user add the Inter `<link>` in their `<head>`.

**`<html>` or `<body>` has inline styles that conflict**: The CSS uses specific selectors (`html`, `body` for overrides in print only) and marks print rules `!important`. Should be collision-safe but double-check if the user reports issues.

### 7. Report what was added

After injection, tell the user:
- The file's new size (roughly +12KB unminified)
- The three features to try: press `P` to print, arrow keys to navigate, `?` to see the help panel
- That the nav is auto-hidden by default — moving the mouse reveals it

## Updating an existing injection

If the user asks to update the frame on a deck that already has it:

1. Find both markers (`<!-- slate-frame:start` and `<!-- slate-frame:end -->`)
2. Use Edit to replace everything between (and including) the markers with a freshly composed block from the current asset files
3. Report the version change

## Removing the frame

If the user asks to remove the frame:

1. Delete everything between `<!-- slate-frame:start` and `<!-- slate-frame:end -->` (inclusive, including the markers)
2. Confirm the deck still opens and renders without the nav

## Customization cheat sheet

After injection, common adjustments:

| Want to… | Edit… | Change… |
|---|---|---|
| Nav in a different corner | injected CSS | `.dfnav { right: 20px; bottom: 20px; }` |
| Different auto-hide timing | injected JS | `const HIDE_DELAY = 2400;` |
| Different slide selector | injected JS | `const SLIDE_SELECTOR = '.slide';` |
| Different print page size | injected CSS | `@page { size: 1400px 787px; }` |
| Disable auto-hide | injected JS | remove `hideTimer` logic, keep `nav.classList.add('dfnav-visible')` always-on |

## Files in this skill

- `assets/frame.css` — the stylesheet block
- `assets/frame-markup.html` — the nav + help panel DOM
- `assets/frame.js` — the keyboard/scroll/URL navigation script
