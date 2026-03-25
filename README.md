<div align="center">

# tools.aaris.tech

**A self-hosted collection of web-based utilities** — clean, fast, no sign-up required.

Built with vanilla HTML/CSS/JS on the frontend and a Flask API on the backend,<br>
served through Nginx and Docker Compose.

[Live Site](https://tools.aaris.tech) · [Changelog](CHANGELOG.md)

</div>

---

## Tools

| Tool | Description | Tag |
|------|-------------|-----|
| **Text Fixer** | Fix spelling and grammar with AI — powered by Llama 3.1 | `ai` |
| **EPUB to PDF** | Accessible EPUB to tagged PDF conversion with TTS-friendly reading order | `converter` |
| **Web Novel to PDF** | Export a supported web novel URL to a tagged PDF for offline TTS | `converter` |
| **File Share** | Upload a file, get a shareable link — auto-deleted on expiry | `share` |
| **JSON Formatter** | Paste messy JSON and get it pretty-printed instantly | `dev` |
| **Unit Converter** | Convert time, data, bandwidth, frequency, power, temperature and more | `utility` |
| **Date Calculator** | Add/subtract time from a date, or find the difference between two | `utility` |
| **Download Time Calculator** | Estimate download duration based on speed and file size | `utility` |
| **Ticket Ranker** | Prioritize tickets with pairwise comparisons | `productivity` |

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Browser                                             │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  Nginx (tools container)              port 8080 → 80 │
│  ├── /              → static landing page            │
│  ├── /tools/*       → static tool HTML/CSS/JS        │
│  ├── /manifest.json → auto-generated tool list       │
│  └── /api/*         → proxy to converter:5000        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  Flask / Gunicorn (converter container)   port 5000  │
│  ├── POST /api/fix-text          → Ollama (ai-01)   │
│  ├── POST /api/convert/epub-to-pdf → Calibre + WeasyPrint │
│  ├── POST /api/convert/web-novel-to-pdf → Royal Road + WeasyPrint │
│  ├── POST /api/share/upload      → SQLite + disk     │
│  ├── GET  /api/share/<key>/info                      │
│  ├── POST /api/share/<key>/download                  │
│  └── GET  /api/health                                │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  Ollama — ai-01 (10.10.8.10:11434)                   │
│  └── llama3.1 (8B, Q4_K_M) on Tesla M10 GPU         │
└──────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone git@github.com:jonarihen/tools-platform.git
cd tools-platform
cp .env.example .env
# Set a strong ADMIN_PASSWORD in .env before starting
docker compose up --build -d
```

The platform is available at **http://localhost:8080**.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSWORD` | Required | Admin password for `/tools/ocistrator/` and `/api/admin/*` |
| `OLLAMA_URL` | `http://10.10.8.10:11434` | Ollama API endpoint for the Text Fixer tool |
| `OLLAMA_MODEL` | `llama3.1` | Model to use for text correction |

Set these in `.env` or your shell environment before running `docker compose up`.

## Project Structure

```
tools-platform/
├── docker-compose.yml
├── Dockerfile                 # Nginx + entrypoint
├── entrypoint.sh              # Auto-discovers tools → manifest.json
├── nginx.conf
├── public/
│   ├── index.html             # Landing page (reads manifest.json)
│   ├── style.css              # Shared design system
│   └── favicon.svg
├── converter-api/
│   ├── Dockerfile             # Python 3.12 + Calibre + WeasyPrint + Gunicorn
│   ├── app.py                 # Flask API (conversion, file share, text fixer)
│   └── requirements.txt
└── tools/                     # Each tool is a self-contained directory
    ├── text-fixer/
    ├── epub-to-pdf/
    ├── web-novel-to-pdf/
    ├── file-share/
    ├── json-formatter/
    ├── unit-converter/
    ├── date-calculator/
    ├── download-time-calculator/
    ├── ticket-ranker/
    └── add-tool-guide/
```

## Adding a New Tool

Each tool lives in its own directory under `tools/`:

```
tools/my-tool/
├── index.html    ← self-contained frontend (HTML + CSS + JS)
└── meta.json     ← metadata for the platform
```

**meta.json:**

```json
{
  "name": "My Tool",
  "description": "What it does in one sentence",
  "icon": "🔧",
  "tag": "utility",
  "order": 10
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name on the homepage |
| `description` | Yes | Short description shown on the card |
| `icon` | No | Emoji icon (defaults to 🔧) |
| `tag` | No | Category label shown on the card |
| `order` | No | Sort order on homepage (lower = first) |

The `entrypoint.sh` script auto-discovers all tools and generates `manifest.json` on container startup — no other files need to change. Just add the directory, rebuild, and it appears on the landing page.

The `tools/` directory is volume-mounted, so you can edit tool files without rebuilding the image. Only the manifest regeneration requires a restart.

A full guide is available at `/tools/add-tool-guide/` on the live site.

## Security

The platform is hardened for public-facing deployment:

- **Passwords** — file share passwords are hashed with scrypt (salted, constant-time comparison)
- **Rate limiting** — per-IP limits on all write endpoints (uploads, text fixer, slug checks)
- **Prompt injection** — text fixer uses a hardened system prompt + output length cap to limit abuse
- **CSP** — Content-Security-Policy restricts scripts, styles, fonts, and connections to known origins
- **Headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection` on all responses
- **No auth on Ollama** — relies on network-level access control (private subnet only)

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML, CSS, JS · Outfit + JetBrains Mono fonts |
| Backend | Python 3.12 · Flask · Gunicorn (1 worker, 8 threads) |
| AI | Ollama · Llama 3.1 8B (Q4_K_M) · Tesla M10 GPU |
| Conversion | Calibre (EPUB ingest) + WeasyPrint (tagged PDF output) + Royal Road HTML export |
| Database | SQLite (WAL mode) for file share metadata |
| Proxy | Nginx (Alpine) |
| Infra | Docker Compose · named volumes for persistence |
