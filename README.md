# Vital Core - Health & Wellness Website

Live: **https://vital-core.site**

## Local dev (static + admin API)

This repo includes a tiny local dev server (`dev_server.py`) that:

- serves the static site from the repo root
- exposes a **local-only** JSON API at `/api` backed by SQLite (`data/admin.db`)
- lets you use the single-file admin UI at `/admin`

### Start the dev server

```bash
cd vital-core-site
python3 dev_server.py
# or choose a port:
# PORT=8001 python3 dev_server.py
```

Open:

- Site: <http://127.0.0.1:8001/>
- Admin UI: <http://127.0.0.1:8001/admin/>

### Admin HOWTO (add/edit a product or post)

1. Open the admin UI: <http://127.0.0.1:8001/admin/>
2. Choose a language (`en` / `de`).
3. **Products**
   - Click **New product**
   - Fill `Title` (slug auto-fills; you can edit it)
   - Add image + affiliate URL (optional validation helps)
   - Press **Save** (shortcut: **Ctrl/Cmd+S**)
4. **Blog posts**
   - Switch to **Blog posts**
   - Click **New post**
   - Fill `Title` + `Slug` + optional excerpt/content
   - Set `Published at` (ISO 8601) or leave it empty to default to “now”
   - Press **Save** (shortcut: **Ctrl/Cmd+S**)

Reset local content (optional): stop the server and delete `data/admin.db`.

## Deploy to Cloudflare

```bash
cd vital-core-site
./deploy.sh
```

## Security note

- `dev_server.py` + `/admin` are intended for **local/LAN testing only**.
- In production, the admin/API should be protected (e.g. **Cloudflare Access** in front of the real Worker API).

## Project structure (high level)

```
vital-core-site/
├── admin/              # single-file admin UI
├── data/               # local sqlite db (dev only)
├── dev_server.py       # local static server + /api
├── index.html          # homepage
├── blog.html           # blog listing
├── recipes.html        # recipes catalog
├── about.html          # about page
├── css/                # styles
└── js/                 # scripts
```
