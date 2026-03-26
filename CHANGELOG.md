# Changelog

All notable changes to tools.aaris.tech are documented here.

---

## [Unreleased]

### Ticket Ranker improvements
- **Keyboard ranking** — the ranking screen now supports `←` and `→` so you can pick the left or right ticket without leaving the keyboard
- **Fast mode for large lists** — for 16+ tickets, the tool can now pre-rank tickets in groups of 4 before ordering those groups, cutting the number of decisions for long queues
- **Clearer ranking UI** — the sorter now shows the active key hints on-screen and lets you re-rank a fast-mode result with a full exact pass

### Added — Web Novel to PDF tool (`/tools/web-novel-to-pdf/`)
- Export a supported web novel URL to a tagged PDF for offline TTS and screen readers
- Royal Road support reads the fiction table of contents, fetches chapters in order, and renders a structured PDF from clean HTML instead of screen-positioned text
- Optional inclusion of Royal Road author notes in the output
- Server-side export is rate-limited and restricted to supported hosts to avoid turning the endpoint into a generic fetch proxy
- Scribble Hub URLs are validated but currently return a clear upstream-blocked error because the site serves a Cloudflare challenge to this server

### EPUB to PDF accessibility
- **Tagged PDF output** — EPUB-to-PDF conversion now renders the final PDF with WeasyPrint instead of Calibre's PDF engine, producing tagged PDFs with a structure tree for better screen reader and TTS support
- **Reading order fix** — conversion now goes through Calibre HTMLZ output first, then renders from HTML order to avoid the broken line ordering produced by Calibre's PDF coordinate system
- **Accessible metadata** — generated PDFs now inherit title, author, and language metadata from the EPUB where available, with a fallback document title for PDF/UA generation
- **Tool copy update** — the EPUB to PDF tool now advertises accessible tagged PDF output instead of page numbers/table-of-contents features that were tied to the old renderer

### Security hardening
- **Password hashing** — replaced unsalted SHA-256 with werkzeug's scrypt (salted, constant-time comparison) for file share passwords
- **Password no longer in URL** — file share download sends password via POST body instead of query parameter, preventing leaks in browser history, server logs, and referer headers
- **Rate limiting** — added per-IP limits to file uploads (10/hr), slug checks (30/min); text fixer already had 10/min
- **Share password throttling** — failed password attempts on protected file shares are now rate-limited to slow brute-force attacks
- **Tracking endpoint hardening** — `/api/track` is now rate-limited and only accepts the expected public client events
- **Admin password required** — admin auth no longer falls back to `changeme`; deployment now requires `ADMIN_PASSWORD` to be set
- **Content Security Policy** — added CSP header in nginx restricting scripts, styles, fonts, and connections to known origins
- **Flask security headers** — all API responses now include `X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN`
- **Error sanitisation** — text fixer stream no longer leaks internal exception details to clients
- **Security logging** — failed password attempts and rate limit violations are now logged with client IP

### Reliability & infrastructure improvements
- **Docker healthcheck** — converter container is health-probed every 30s via `/api/health`; tools container waits for healthy status before starting
- **Stale job cleanup** — background thread removes undownloaded EPUB conversion jobs after 1 hour, preventing unbounded memory growth
- **Rate limiter pruning** — background thread removes inactive IPs from rate limit stores hourly, preventing slow memory leak
- **Ollama URL configurable** — `OLLAMA_URL` and `OLLAMA_MODEL` are now environment variables in `docker-compose.yml`, configurable without rebuild
- **Single gunicorn worker + 8 threads** — keeps in-memory EPUB jobs, admin sessions, and rate-limit state consistent across requests while still allowing concurrent API traffic
- **No-cache on tool HTML** — nginx sends `Cache-Control: no-cache` on tool `index.html` pages so users always get fresh content after deploys
- **Diff memory cap** — lowered LCS diff threshold in text fixer to prevent ~8 MB memory spikes on long texts
- **add-tool-guide consistency** — now uses shared `style.css` and favicon like all other tools
- **Lightweight share verification** — unlocking a password-protected file share now checks credentials without downloading the file twice

### Added — Text Fixer tool (`/tools/text-fixer/`)
- AI-powered spelling and grammar fixer using Llama 3.1 8B via Ollama (ai-01 server)
- Streaming response with real-time typewriter effect
- Word-level diff view showing additions (green) and removals (red strikethrough)
- Hardened system prompt to resist prompt injection — model is instructed to only proofread and ignore embedded instructions
- Per-IP rate limiting: 10 requests per minute (HTTP 429 when exceeded)
- Output length cap: stream is cut if response exceeds 2x input length + 200 chars, preventing abuse as a general-purpose chatbot
- 10,000 character input limit with 120s timeout
- Backend streams via SSE through the existing Flask converter API (`POST /api/fix-text`)
- `X-Accel-Buffering: no` header ensures nginx does not buffer the SSE stream
- Added `requests` to `converter-api/requirements.txt`

### Added — File Share tool (`/tools/file-share/`)
- Upload any file and receive a shareable link
- Files are automatically deleted after expiry (default 24 hours)
- Drag-and-drop or click-to-browse upload with progress bar
- **Custom slug** — choose a human-readable link ID (e.g. `?id=my-file`) instead of a random token; live availability check as you type with 400ms debounce
- **Custom expiry** — pick from 1 h, 6 h, 12 h, 24 h, 48 h, 3 days, or 7 days
- **Password protection** — optionally require a password to download; passwords are hashed with scrypt (salted) server-side, never stored in plain text
- Download page shows filename, size, and time remaining; prompts for password when required
- Server-side storage cap: rejects new uploads when total stored files exceed 50 GB
- Per-file size limit: 5 GB
- Background cleanup thread removes expired files from disk every 5 minutes

### Changed
- `nginx.conf` — disabled `proxy_request_buffering`, set `client_max_body_size 0` (unlimited, app handles limits), raised all timeouts to 3600s
- `converter-api/Dockerfile` — raised gunicorn worker timeout to 3600s
- `converter-api/app.py` — set `MAX_CONTENT_LENGTH` for Flask/Werkzeug; large file uploads now stream to disk in 1 MB chunks instead of loading the entire file into memory; added 413 error handler
- **NPM (Nginx Proxy Manager)** — requires `client_max_body_size 10G`, `proxy_request_buffering off`, `proxy_buffering off`, `proxy_max_temp_file_size 0`, and extended timeouts in the Advanced config for large uploads to pass through

### Added — SQLite metadata persistence
- `docker-compose.yml` — added named Docker volume `shares-data` mounted at `/app/shares` in the converter container; uploaded files now survive container restarts and rebuilds
- `converter-api/app.py` — replaced in-memory `_shares`/`_slug_to_id` dicts with a SQLite database (`/app/shares/shares.db`) using Python's built-in `sqlite3` module (no new dependencies)
- Database uses WAL journal mode for safe concurrent reads
- Share metadata (filename, slug, expiry, password hash, size) now persists across restarts — existing share links and passwords continue to work after a redeploy
- 50 GB storage cap now queries `SUM(size)` from the DB so it remains accurate across restarts

---

## [1.0.0] — Initial release

### Added
- Platform landing page with tool card grid, loaded from `manifest.json`
- JSON Formatter — format, minify, validate and copy JSON
- Unit Converter — convert between common units
- Date Calculator — calculate differences between dates
- Download Time Calculator — estimate file download time
- Ticket Ranker — rank and prioritise support tickets
- EPUB to PDF converter — server-side conversion via Calibre with progress tracking
- How to Add a Tool guide
- Shared design system (`/public/style.css`, `/public/favicon.svg`)
- Nginx + Docker Compose setup with converter API proxy
