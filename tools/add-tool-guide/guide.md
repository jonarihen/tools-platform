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

This is your actual tool. It must be a **fully self-contained HTML file** — everything it needs must be either inline or loaded from a CDN.

#### Minimal template:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Tool – tools.aaris.tech</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      background: linear-gradient(160deg, #0c0c0f 0%, #141420 40%, #0f1118 100%);
      font-family: 'Outfit', sans-serif;
      color: #e8e8ed;
    }
    .container { max-width: 720px; margin: 0 auto; padding: 48px 24px 80px; }
    .back {
      display: inline-block; margin-bottom: 12px; font-size: 13px;
      font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.2);
      text-decoration: none; letter-spacing: 0.1em;
    }
    h1 {
      font-size: 40px; font-weight: 700; letter-spacing: -0.03em;
      background: linear-gradient(135deg, #f8f8ff 0%, #a0a0b8 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      text-align: center; margin-bottom: 8px;
    }
    .subtitle {
      text-align: center; font-size: 16px;
      color: rgba(255,255,255,0.45); font-weight: 300; margin-bottom: 40px;
    }
  </style>
</head>
<body>
  <div class="container">
    <a href="/" class="back">← tools.aaris.tech</a>
    <h1>My Tool Name</h1>
    <p class="subtitle">Short description of the tool</p>

    <!-- Your tool UI here -->

  </div>
  <script>
    // Your tool logic here
  </script>
</body>
</html>
```

### Step 4: Restart the container

```bash
docker compose restart
```

That's it. The tool now appears on the homepage and is accessible at its URL.

---

## Design Guidelines

All tools should follow this visual style to look consistent with the platform:

### Required fonts (load from Google Fonts):

```html
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

- **Outfit** — primary UI font (headings, body text, buttons)
- **JetBrains Mono** — monospace accent font (labels, tags, numbers, code)

### Color palette:

```css
/* Background */
background: linear-gradient(160deg, #0c0c0f 0%, #141420 40%, #0f1118 100%);

/* Text colors */
color: #e8e8ed;                      /* Primary text */
color: rgba(255,255,255,0.75);       /* Secondary text */
color: rgba(255,255,255,0.45);       /* Muted text */
color: rgba(255,255,255,0.25);       /* Faint text / hints */
color: rgba(255,255,255,0.2);        /* Barely visible */

/* Accent color (amber/gold) */
color: #f59e0b;
background: rgba(245,158,11,0.15);
border-color: rgba(245,158,11,0.3);

/* Secondary accent (blue) */
color: #3b82f6;

/* Surfaces */
background: rgba(255,255,255,0.02);  /* Card background */
background: rgba(255,255,255,0.04);  /* Slightly raised surface */
background: rgba(255,255,255,0.06);  /* Button / badge background */

/* Borders */
border: 1px solid rgba(255,255,255,0.06);  /* Subtle */
border: 1px solid rgba(255,255,255,0.08);  /* Default */
border: 1px solid rgba(255,255,255,0.1);   /* Emphasized */
border: 1px solid rgba(255,255,255,0.15);  /* Hover state */
```

### Common CSS base (include in every tool):

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  min-height: 100vh;
  background: linear-gradient(160deg, #0c0c0f 0%, #141420 40%, #0f1118 100%);
  font-family: 'Outfit', sans-serif;
  color: #e8e8ed;
}
```

### Component patterns:

**Page container:**
```css
.container {
  max-width: 720px;    /* or 960px for wider tools */
  margin: 0 auto;
  padding: 48px 24px 80px;
}
```

**Back link to homepage (include at top of every tool):**
```html
<a href="/" class="back">← tools.aaris.tech</a>
```

```css
.back {
  display: inline-block; margin-bottom: 12px; font-size: 13px;
  font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.2);
  text-decoration: none; letter-spacing: 0.1em;
}
```

**Page title:**
```css
h1 {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #f8f8ff 0%, #a0a0b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
}
```

**Text input:**
```css
input[type="text"], input[type="number"], textarea {
  padding: 14px 18px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  color: #e8e8ed;
  font-size: 15px;
  font-family: 'Outfit', sans-serif;
  outline: none;
  width: 100%;
}
```

**Primary button (amber accent):**
```css
.btn-primary {
  padding: 16px 32px;
  background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05));
  border: 1px solid rgba(245,158,11,0.3);
  border-radius: 14px;
  color: #f59e0b;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Outfit', sans-serif;
  cursor: pointer;
}
```

**Secondary button:**
```css
.btn-secondary {
  padding: 14px 24px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  color: rgba(255,255,255,0.6);
  font-size: 14px;
  font-weight: 500;
  font-family: 'Outfit', sans-serif;
  cursor: pointer;
}
```

**Card / list item:**
```css
.card {
  padding: 14px 18px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
}
```

**Small tag / badge:**
```css
.tag {
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.1em;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.4);
}
```

**Fade-in animation:**
```css
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
```

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
7. Include the back link — every tool should have a `← tools.aaris.tech` link back to the homepage

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
- Tool loads the correct fonts (Outfit + JetBrains Mono)
- Tool uses the dark theme (dark background, light text)
- Tool has a back link to the homepage
- Title tag follows format: `Tool Name – tools.aaris.tech`
- Run `docker compose restart` to pick up the new tool
