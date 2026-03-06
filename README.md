# tools.aaris.tech

A modular collection of everyday web tools. Each tool is a self-contained folder — add a new one without touching docker-compose.

## Quick Start

```bash
docker compose up -d --build
```

Open `http://localhost:8080` (or your domain).

## Adding a New Tool

1. Create a folder inside `tools/`:

```
tools/
  my-new-tool/
    meta.json
    index.html
```

2. Create `meta.json`:

```json
{
  "name": "My New Tool",
  "description": "What this tool does",
  "icon": "🔧",
  "tag": "utility",
  "order": 10
}
```

| Field         | Required | Description                                  |
|---------------|----------|----------------------------------------------|
| `name`        | ✅       | Display name on the homepage                 |
| `description` | ✅       | Short description shown on the card          |
| `icon`        | ❌       | Emoji icon (defaults to 🔧)                  |
| `tag`         | ❌       | Category label shown on the card             |
| `order`       | ❌       | Sort order on homepage (lower = first)        |

3. Create `index.html` — your tool as a self-contained page. Use CDN imports for any libraries you need.

4. Restart the container:

```bash
docker compose restart
```

The entrypoint script scans `tools/*/meta.json` on every startup and regenerates the homepage manifest automatically.

## Structure

```
tools-platform/
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh          # Scans tools/ and generates manifest.json
├── nginx.conf
├── public/
│   └── index.html         # Homepage — reads manifest.json
└── tools/                  # ← Your tools go here (volume-mounted)
    └── ticket-ranker/
        ├── meta.json
        └── index.html
```

## Tips

- Each tool is completely independent — use any framework, plain HTML, whatever you want
- Static assets (images, CSS, JS) can live in the tool's folder and be referenced with relative paths
- For React tools, use `<script src="https://cdnjs.cloudflare.com/...">` from CDN
- The `tools/` directory is volume-mounted, so you can edit tools without rebuilding the image
- Only the manifest regeneration requires a restart (or you can `docker exec tools-aaris /entrypoint.sh` to refresh)
