# Server-Side EPUB to PDF — Upgrade Instructions

This adds a Calibre-powered converter API as a sidecar container.

## What changed

- `docker-compose.yml` — added `converter` service
- `nginx.conf` — added `/api/` proxy to converter
- `converter-api/` — new folder next to docker-compose.yml (the API)
- `tools/epub-to-pdf/` — updated to use server-side conversion

## Installation

```bash
# From your tools-platform directory:

# 1. Copy the converter-api folder
cp -r converter-api/ /path/to/tools-platform/converter-api/

# 2. Replace docker-compose.yml
cp docker-compose.yml /path/to/tools-platform/docker-compose.yml

# 3. Replace nginx.conf
cp nginx.conf /path/to/tools-platform/nginx.conf

# 4. Replace the epub-to-pdf tool
cp -r epub-to-pdf/* /path/to/tools-platform/tools/epub-to-pdf/

# 5. Rebuild and restart
cd /path/to/tools-platform
docker compose up -d --build
```

The first build will take a few minutes (downloading Calibre ~400MB).
After that, restarts are instant.
