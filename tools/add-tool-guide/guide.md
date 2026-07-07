# tools.aaris.tech — How to Add New Tools

## Context for AI Assistants

This is a modular web toolbox platform running in Docker. The homepage at tools.aaris.tech automatically discovers and displays all tools. Each tool is a self-contained folder inside the `tools/` directory. No config files, Docker files, or existing code needs to be modified when adding a new tool.

---

## Architecture Overview

```
tools-platform/
├── docker-compose.yml          # DO NOT MODIFY
├── Dockerfile                  # DO NOT MODIFY
├── entrypoint.sh               # Scans tools/ on startup, generates manifest.json
├── nginx.conf                  # Serves static files + proxies /api/ to converter
├── converter-api/              # Server-side conversion API (Calibre + Flask)
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── public/
│   └── index.html              # Homepage — fetches /manifest.json and renders tool cards
└── tools/                      # ← ALL TOOLS LIVE HERE
    ├── ticket-ranker/          # Example tool
    │   ├── meta.json
    │   └── index.html
    ├── your-new-tool/          # Just add a folder like this
    │   ├── meta.json
    │   └── index.html
    └── another-tool/
        ├── meta.json
        ├── index.html
        └── (any other static files the tool needs)
```

### How auto-discovery works

1. On container startup, `entrypoint.sh` scans every `tools/*/meta.json` file
2. It builds a `manifest.json` array with each tool's metadata + its folder name as `slug`
3. The homepage (`public/index.html`) fetches `/manifest.json` and renders a card grid
4. Each card links to `/tools/{slug}/` which serves that tool's `index.html`

This means: **drop a folder in `tools/`, restart the container, done.**

---

## Step-by-Step: Adding a New Tool

### Step 1: Create the folder

Pick a slug (lowercase, hyphens, no spaces). This becomes the URL path.

```bash
mkdir tools/my-tool-name
```

The tool will be accessible at: `https://tools.aaris.tech/tools/my-tool-name/`

### Step 2: Create `meta.json`

This file tells the homepage what to display. Create `tools/my-tool-name/meta.json`:

```json
{
  "name": "My Tool Name",
  "description": "A short sentence about what this tool does",
  "icon": "🔧",
  "tag": "utility",
  "order": 10
}
```

#### Field reference:

| Field | Required | Type | Description |
|---|---|---|---|
| `name` | YES | string | Display name shown on the homepage card |
| `description` | YES | string | Short description (1-2 sentences) shown on the card |
| `icon` | no | string | Single emoji shown on the card. Defaults to 🔧 |
| `tag` | no | string | Small label shown on the card (e.g. "productivity", "dev", "finance") |
| `order` | no | number | Sort priority on homepage. Lower number = shown first. Default: 99 |

**Important:** The JSON must be valid. No trailing commas, no comments.

### Step 3: Create `index.html`

This is your actual tool. It must be a **fully self-contained HTML file** — everything it needs must be either inline or loaded from a CDN. The platform serves a shared design-system stylesheet at `/style.css` (the AARIS design language) — always link it before your own styles.

#### Minimal template:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Tool – tools.aaris.tech</title>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62.5..125,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/style.css">
  <style>
    /* Page-specific styles only. Use the shared CSS custom properties
       (var(--accent), var(--line), ...) — never hard-coded colors. */
    .container { max-width: 720px; }
  </style>
</head>
<body>
  <nav class="topbar">
    <a href="/" class="topbar-brand">TOOLS.AARIS.TECH</a>
    <span class="topbar-path">/ TOOLS / MY-TOOL-NAME</span>
    <span class="topbar-right"><span class="led led-ok" aria-hidden="true"></span>OPERATIONAL</span>
  </nav>

  <div class="container">
    <header class="tool-head">
      <div class="tool-kicker">01 / UTILITY</div>
      <h1>My Tool Name</h1>
      <p class="subtitle">Short description of the tool.</p>
      <div class="rule"></div>
    </header>

    <!-- Your tool UI here -->

  </div>
  <script>
    // Your tool logic here
  </script>
<script src="/track.js"></script>
</body>
</html>
```

### Step 4: Restart the container

```bash
docker compose restart
```

That's it. The tool now appears on the homepage and is accessible at its URL.

---

## Design Guidelines — the AARIS design language

The platform uses the **AARIS design language**: a dark, square, thin-bordered, orange-accent "operator console" style. It should feel like a homelab dashboard or a datacenter asset tag — technical, readable, low-noise. Not a generic SaaS page.

Most of it is already implemented in the shared stylesheet at **`/style.css`** — link it and you get the page background + grid, typography, buttons, form controls, status boxes, tags, LEDs, and toasts for free. Your inline `<style>` should only contain page-specific layout.

### Required fonts (load from Google Fonts):

```html
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62.5..125,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- **Archivo** — primary UI font. Headings are heavy (800–900), uppercase, slightly expanded (`font-stretch: 110–125%`)
- **IBM Plex Mono** — monospace for labels, tags, numbers, metadata, buttons, timestamps

### Design tokens (defined in `/style.css`, use them everywhere):

```css
var(--bg)        /* #0e1014  page background */
var(--bg-raise)  /* #12151a  cards, panels */
var(--bg-input)  /* #0b0d11  input fields */
var(--ink)       /* #e9ecef  primary text */
var(--muted)     /* #8b939e  secondary text */
var(--dim)       /* #4d545e  low-priority metadata */
var(--line)      /* #232830  borders */
var(--line-soft) /* #1a1e25  internal dividers */
var(--accent)    /* #ff5a1f  THE action color (orange) */
var(--ok)        /* #3fd97f  healthy status only */
var(--warning)   /* #ffb224  warnings/activity only */
var(--danger)    /* #e5484d  errors only */
var(--font-sans) / var(--font-mono)
```

### Hard rules:

- **Square corners** — `border-radius: 0` everywhere. No pills, no rounded cards.
- **Thin borders, no shadows** — `1px solid var(--line)`, never `box-shadow`.
- **Orange is the only accent** — active states, primary buttons, hover borders. Green/amber are for status LEDs only, never decoration. No blue/purple accents.
- **Mono labels** — every label, tag, hint, and counter is `var(--font-mono)`, uppercase, letter-spaced.
- **Never hard-code colors** — always the tokens above.
- Respect `prefers-reduced-motion` (the shared stylesheet already disables animation for it).

### Shared components you get from `/style.css` (just use the class names):

| Class / element | What it gives you |
|---|---|
| `.topbar`, `.topbar-brand`, `.topbar-path`, `.topbar-right` | Fixed top status bar (see template) |
| `.tool-head`, `.tool-kicker`, `h1`, `.subtitle`, `.rule` | Standard tool header block |
| `.btn-primary` | Orange-filled primary action button |
| `.btn-secondary` | Thin-bordered secondary button (hover → orange border) |
| `input`, `select`, `textarea`, `label` | Already fully styled — dark inset fields, orange focus |
| `.status.ok` / `.status.error` / `.status.info` | Status message boxes |
| `.panel`, `.panel-title` | Bordered raised panel with mono header |
| `.tag`, `.badge` | Small bordered mono uppercase labels |
| `.led.led-ok` / `.led-warning` / `.led-error` / `.led-off` / `.led-blink` | 8px square status LEDs |
| `.dropzone` | Dashed-border file drop area |
| `.spinner` | Blinking-LED loading indicator |
| `.toast` | Fixed bottom toast |
| `.hidden` | `display: none !important` |
| `@keyframes fadeIn` / `fadeSlideIn` | Shared entry animations |

### Page-specific styles:

Set your container width and lay out your panels — that's usually all you need:

```css
.container { max-width: 720px; }   /* 640–980px depending on the tool */
.my-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
```

### Writing style:

Direct and practical, like a technical person wrote it — not marketing. "Convert files without sending them to a random cloud service", not "Unlock seamless digital experiences". Uppercase mono for labels (`PAGE SIZE`, `EXPIRES AFTER`), plain sentences for descriptions.

---

## Using JavaScript Frameworks

Tools are static HTML files. If you need a framework, load it from a CDN.

### Plain JavaScript (preferred for simple tools)
No extra setup needed. Just use a script tag in the HTML.

### React (for interactive tools)
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.9/babel.min.js"></script>

<div id="root"></div>
<script type="text/babel">
  const { useState, useRef, useEffect } = React;

  function App() {
    return <div>Your React app here</div>;
  }

  ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
```

### Other useful CDN libraries
```html
<!-- Chart.js for charts -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>

<!-- Day.js for dates -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.11.10/dayjs.min.js"></script>

<!-- Marked for Markdown rendering -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/11.1.1/marked.min.js"></script>
```

Find more at: https://cdnjs.cloudflare.com

---

## Additional Files

Tools can include extra static files (CSS, JS, images, JSON data). Reference them with relative paths:

```
tools/my-tool/
├── meta.json
├── index.html
├── style.css
├── app.js
└── data/
    └── defaults.json
```

---

## Server-Side API

The platform includes a server-side converter API accessible at `/api/`. Tools can use it for heavy processing that can't be done client-side. The API is proxied through Nginx — tools just make requests to `/api/...` and it works.

### Available endpoints

**EPUB to PDF conversion:**
```
POST /api/convert/epub-to-pdf
Content-Type: multipart/form-data

Form fields:
  file        - the .epub file (required)
  page_size   - "a4", "letter", or "a5" (default: "a4")
  margin      - margin in mm: "10", "15", "20", "25" (default: "15")
  font_size   - font size in px: "10", "12", "14", "16" (default: "12")

Response: the converted PDF file as a download
```

**Health check:**
```
GET /api/health
Response: { "status": "ok" }
```

### How to call the API from a tool

```javascript
// Example: uploading a file to the converter
var formData = new FormData();
formData.append('file', fileObject);
formData.append('page_size', 'a4');

var response = await fetch('/api/convert/epub-to-pdf', {
  method: 'POST',
  body: formData
});

if (response.ok) {
  var blob = await response.blob();
  // trigger download, display result, etc.
}
```

### Adding new API endpoints

New endpoints can be added to `converter-api/app.py` (a Flask app backed by Calibre). The converter service has Calibre's `ebook-convert` CLI available, which supports many formats including EPUB, MOBI, AZW3, DOCX, HTML, TXT, PDF, and more. If a tool needs a new conversion route, it can be added there and will be available at `/api/your-new-route`.

Most tools should still be purely client-side. Only use the API when you need server-side processing like file format conversion.

---

## Rules and Constraints

1. Every tool MUST have both `meta.json` and `index.html` — missing either means the tool won't appear or won't work
2. Everything must be self-contained — no build steps, no npm, no bundlers. It's all static files served by Nginx
3. Tools are client-side (HTML/CSS/JS) but can call the built-in `/api/` endpoints for server-side processing (see Server-Side API section above)
4. Folder name = URL slug — use lowercase letters, numbers, and hyphens only (e.g. `password-generator`, `json-formatter`)
5. Don't modify anything outside the `tools/` directory — the platform files should never be changed
6. Valid JSON only in `meta.json` — no comments, no trailing commas
7. Include the fixed `.topbar` — its `TOOLS.AARIS.TECH` brand is the link back to the homepage

---

## Output Format

When building a tool, output EXACTLY two files:

**FILE 1:** `meta.json`
**FILE 2:** `index.html`

Both go inside a folder named with the tool's slug (e.g. `tools/my-tool-name/`).

---

## Deployment Checklist

- `tools/my-tool/meta.json` exists and is valid JSON
- `tools/my-tool/index.html` exists and is a complete HTML page
- Links the shared stylesheet: `<link rel="stylesheet" href="/style.css">`
- Loads the correct fonts (Archivo + IBM Plex Mono)
- Has the fixed `.topbar` with brand link back to the homepage
- Uses the standard `.tool-head` header (kicker, h1, subtitle, rule)
- Uses design tokens (`var(--accent)` etc.), square corners, no shadows
- Includes `<script src="/track.js"></script>` before `</body>`
- Title tag follows format: `Tool Name – tools.aaris.tech`
- Run `docker compose restart` to pick up the new tool
