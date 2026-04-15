# slate-mcp

MCP server for Slate. Lets any MCP-aware client (Claude Desktop, Claude Code, etc.) generate a complete Slate-compatible HTML deck from a single instruction.

## Why

Team members shouldn't have to copy-paste a prompt and save HTML files manually. With this server installed:

> **You**: Make me a 10-slide Slate deck about our Q4 roadmap for the board. Prepared by Priya. Save it to `~/Desktop/q4-board.html`.
>
> **Claude**: [calls `slate_create_deck`] Done — 10-slide deck saved to `~/Desktop/q4-board.html`. Want me to open it in the viewer?

No prompt copy-paste, no manual save, iteration-friendly.

## Tools exposed

| Tool | What it does |
|---|---|
| `slate_create_deck` | Generate a complete Slate-compliant HTML deck and write it to disk. |
| `slate_apply_frame` | Inject the Slate nav/print chrome into any existing HTML deck so it's standalone-shareable. |
| `slate_list_slide_types` | Return the schema for all 12 slide types so the calling LLM knows what fields each one accepts. |

## Install

Python 3.10 or newer required.

```bash
cd /path/to/Slate/mcp
pip install -e .
```

That makes the `slate-mcp` command available on your PATH and installs the `mcp` SDK dependency.

### For Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "slate": {
      "command": "slate-mcp"
    }
  }
}
```

If you have other MCP servers configured, merge into the existing `mcpServers` object rather than replacing it.

Restart Claude Desktop. You should now be able to ask Claude to make Slate decks.

### For Claude Code

Add to your project's `.mcp.json` or your user config at `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "slate": {
      "command": "slate-mcp"
    }
  }
}
```

Claude Code picks up the tools on next session start.

## How it works

The server exposes `slate_create_deck` with this interface:

```python
slate_create_deck(
    output_path: str,           # e.g. "~/Desktop/pitch.html"
    deck_title: str,            # browser tab + viewer topbar
    brand: str,                 # wordmark in the chrome
    accent_hex: str = "#3D3FB7",# drives the whole palette
    slides: list[dict],         # see slate_list_slide_types()
    include_frame: bool = True, # bake in nav + print chrome
)
```

When Claude decides to call it, it structures the `slides` list as dicts like:

```python
[
  {
    "type": "title",
    "eyebrow": "PRESENTATION · 2026",
    "headline": "A clean point of view, delivered with <em>intent.</em>",
    "subtitle": "A minimal deck template.",
    "meta": [["Prepared by", "Priya"], ["For", "The board"], ["Date", "April 2026"]]
  },
  {
    "type": "agenda",
    "eyebrow": "Agenda",
    "section": "Section 01",
    "headline": "What we'll cover.",
    "items": [
      ["01", "The context", "Where we are today."],
      ["02", "The opportunity", "Why now."],
      ["03", "The plan", "How we get there."],
      ["04", "Next steps", "What we need from you."]
    ]
  },
  ...
]
```

The server renders those into a full HTML file using Slate's design system — Inter typography, cqw-based sizing, hairline rules, alternating light/dark slides, bottom chrome on every slide, meta row on every non-title slide — and (by default) injects the nav/print frame before `</body>` so the deck works standalone.

## Supported slide types

Call `slate_list_slide_types` to see the live schema, but the set is:

| Type | Background | Fields |
|---|---|---|
| `title` | Dark | `eyebrow`, `headline`, `subtitle`, `meta` |
| `agenda` | Light | `eyebrow`, `section`, `headline`, `items` (4 × `[num, title, desc]`) |
| `statement` | Dark | `eyebrow`, `section`, `text` |
| `two_column` | Light | `eyebrow`, `section`, `headline`, `columns` (2 × `[subhead, body]`) |
| `narrative` | Light | Same as `two_column`, for denser copy |
| `stats` | Light | `eyebrow`, `section`, `headline`, `stats` (3 × `[num, label, desc]`) |
| `principles` | Dark | `eyebrow`, `section`, `headline`, `items` (3 × `[index, title, desc]`) |
| `methodology` | Light | `eyebrow`, `section`, `headline`, `stages` (≤5 × `[step, title, body]`) |
| `quote` | Light | `eyebrow`, `section`, `text`, `attribution` |
| `case_study` | Light | `eyebrow`, `section`, `headline`, `case_title`, `narrative`, `proofs` (3 × `[num, label, desc]`) |
| `deliverables` | Light | `eyebrow`, `section`, `headline`, `items` (6 × `[num, title, desc]`) |
| `close` | Dark | `eyebrow`, `section`, `headline`, `body`, `cta_label`, `contact` |

Use `<em>…</em>` inside any headline or body text to render a phrase in the accent colour.

## Troubleshooting

**"Command not found: slate-mcp"**
Make sure `pip install -e .` ran in the `mcp/` directory and that your Python's `bin/` folder is on `PATH`. If you use `pipx` or a virtualenv, install there and reference the absolute path in the MCP config:

```json
{ "mcpServers": { "slate": { "command": "/absolute/path/to/slate-mcp" } } }
```

**"No tools from Slate are showing up in Claude Desktop"**
Fully quit Claude Desktop (Cmd-Q, not just the window) and reopen. The config is only read on launch.

**"It's not using my frame — the colours look generic."**
Check that the repo's `skill/assets/` directory is reachable from the MCP server. By default it's resolved relative to the installed package, so an editable install (`pip install -e .` from the repo) works out of the box. If you moved the package, set `SLATE_SKILL_DIR` to point at `skill/assets/`.

## Versioning

This is `slate-mcp 0.1.0`. Tool signatures may change until 1.0. Lock to a specific commit if stability matters for your team.

## License

MIT. See the main Slate repo.
