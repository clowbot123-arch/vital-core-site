#!/usr/bin/env python3
"""VitalCore local dev server: static site + SQLite-backed admin API.

Runs on http://0.0.0.0:8001
- Serves static files from this repo root
- Provides JSON API under /api
  - GET/POST /api/products
  - PUT/DELETE /api/products/<id>
  - GET/POST /api/posts
  - PUT/DELETE /api/posts/<id>

Security note:
- This is intended for LOCAL/LAN testing only.
- Production should put Cloudflare Access in front of the real Worker API.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import sqlite3
from urllib.parse import parse_qs
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "admin.db"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL,
              lang TEXT NOT NULL,
              title TEXT NOT NULL,
              tag TEXT NOT NULL DEFAULT '',
              description TEXT NOT NULL DEFAULT '',
              bullets_json TEXT NOT NULL DEFAULT '[]',
              price_old TEXT NOT NULL DEFAULT '',
              price_new TEXT NOT NULL DEFAULT '',
              price_unit TEXT NOT NULL DEFAULT '',
              image_url TEXT NOT NULL DEFAULT '',
              affiliate_url TEXT NOT NULL DEFAULT '',
              featured INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL,
              lang TEXT NOT NULL,
              title TEXT NOT NULL,
              category TEXT NOT NULL DEFAULT '',
              excerpt TEXT NOT NULL DEFAULT '',
              hero_image_url TEXT NOT NULL DEFAULT '',
              content_html TEXT NOT NULL DEFAULT '',
              published_at TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_products_lang_active ON products(lang, active)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_posts_lang_active ON posts(lang, active)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_at)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_product_slug_lang ON products(lang, slug) WHERE active=1")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_post_slug_lang ON posts(lang, slug) WHERE active=1")

        # Seed default products once so the admin isn't empty on first open.
        cur = con.execute("SELECT COUNT(*) FROM products")
        n = int(cur.fetchone()[0])
        if n == 0:
            now = utcnow_iso()
            defaults = [
                # EN
                (
                    "menopower-abs-total",
                    "en",
                    "MenoPower Abs TOTAL",
                    "Women 40+",
                    "A simple home ab plan (5–10 minutes/day) designed for consistency, posture, and a stronger core.",
                    json.dumps([
                        "Strong abs and core stability",
                        "Better posture and less back discomfort",
                        "Short sessions that actually fit real life",
                    ]),
                    "€35",
                    "€29",
                    "",
                    "https://images.pexels.com/photos/841130/pexels-photo-841130.jpeg",
                    "https://pilates4life.lpages.co/menopower-bauch-total/#aff=ClawDave",
                    0,
                    1,
                    now,
                    now,
                ),
                (
                    "advanced-amino-acid-complex",
                    "en",
                    "Advanced Amino Acid Complex",
                    "Recovery",
                    "A premium amino acid formula for people who train (or want to keep muscle while dieting) and want better recovery.",
                    json.dumps([
                        "Supports recovery and training consistency",
                        "Helps preserve lean mass during stress or dieting",
                        "Simple daily routine",
                    ]),
                    "€108.80",
                    "€39.95",
                    "",
                    "https://images.pexels.com/photos/3762875/pexels-photo-3762875.jpeg",
                    "https://www.advancedbionutritionals.com/DS24/Advanced-Amino/Muscle-Mass-Loss/HD.htm#aff=ClawDave",
                    1,
                    1,
                    now,
                    now,
                ),
                (
                    "endopeak-vitality-formula",
                    "en",
                    "EndoPeak Vitality Formula",
                    "Men 40+",
                    "A focused pick for men who want better day-to-day energy, stamina, and vitality support.",
                    json.dumps([
                        "Natural energy support",
                        "Endurance and vitality focus",
                        "Easy to use",
                    ]),
                    "€159.37",
                    "€69",
                    "/ bottle",
                    "https://images.pexels.com/photos/3772509/pexels-photo-3772509.jpeg",
                    "https://endopeak24.com/d/order-now.php#aff=ClawDave",
                    0,
                    1,
                    now,
                    now,
                ),
                # DE
                (
                    "menopower-bauch",
                    "de",
                    "MenoPower Bauch TOTAL",
                    "Frauen 40+",
                    "Ein kurzer Bauch-Plan (5–10 Min/Tag) für mehr Stabilität, bessere Haltung und einen starken Core.",
                    json.dumps([
                        "Starker Core und bessere Stabilität",
                        "Bessere Haltung, weniger Rücken-Ziehen",
                        "Kurze Sessions, die wirklich in den Alltag passen",
                    ]),
                    "€35",
                    "€29",
                    "",
                    "https://images.pexels.com/photos/841130/pexels-photo-841130.jpeg",
                    "https://pilates4life.lpages.co/menopower-bauch-total/#aff=ClawDave",
                    0,
                    1,
                    now,
                    now,
                ),
                (
                    "advanced-amino",
                    "de",
                    "Advanced Amino Acid Complex",
                    "Regeneration",
                    "Premium-Aminosäuren für Training, Muskelerhalt und bessere Regeneration.",
                    json.dumps([
                        "Unterstützt Regeneration und Trainingskonstanz",
                        "Hilft beim Muskelerhalt in Diät/Stress",
                        "Einfache tägliche Routine",
                    ]),
                    "€108.80",
                    "€39.95",
                    "",
                    "https://images.pexels.com/photos/3762875/pexels-photo-3762875.jpeg",
                    "https://www.advancedbionutritionals.com/DS24/Advanced-Amino/Muscle-Mass-Loss/HD.htm#aff=ClawDave",
                    1,
                    1,
                    now,
                    now,
                ),
                (
                    "endopeak",
                    "de",
                    "EndoPeak Vitality Formula",
                    "Männer 40+",
                    "Für Männer, die Energie, Ausdauer und Vitalität im Alltag unterstützen wollen.",
                    json.dumps([
                        "Natürliche Energie-Unterstützung",
                        "Fokus auf Ausdauer & Vitalität",
                        "Einfach anzuwenden",
                    ]),
                    "€159.37",
                    "€69",
                    "/ Flasche",
                    "https://images.pexels.com/photos/3772509/pexels-photo-3772509.jpeg",
                    "https://endopeak24.com/d/order-now.php#aff=ClawDave",
                    0,
                    1,
                    now,
                    now,
                ),
            ]
            con.executemany(
                """INSERT INTO products
                   (slug, lang, title, tag, description, bullets_json, price_old, price_new, price_unit,
                    image_url, affiliate_url, featured, active, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                defaults,
            )

        con.commit()


def read_json(handler: SimpleHTTPRequestHandler) -> Any:
    length = int(handler.headers.get("content-length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise ValueError("invalid json") from e


def send_json(handler: SimpleHTTPRequestHandler, data: Any, *, status: int = 200) -> None:
    body = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def bad(handler: SimpleHTTPRequestHandler, msg: str, *, status: int = 400) -> None:
    send_json(handler, {"ok": False, "error": msg}, status=status)


def row_to_dict(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
    d = {desc[0]: row[i] for i, desc in enumerate(cursor.description)}
    return d




def norm_lang(v: Any) -> str:
    lang = str(v or "en").strip().lower()
    return lang if lang in ("en", "de") else "en"


def clean_slug(v: Any) -> str:
    return str(v or "").strip().lower()


def valid_slug(v: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", v))


def valid_http_url_or_empty(v: Any) -> bool:
    from urllib.parse import urlparse

    s = str(v or "").strip()
    if not s:
        return True
    try:
        u = urlparse(s)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


def validate_product_payload(body: dict[str, Any], *, partial: bool = False) -> str | None:
    if (not partial) or ("slug" in body):
        slug = clean_slug(body.get("slug"))
        if not slug:
            return "slug is required"
        if not valid_slug(slug):
            return "invalid slug: use lowercase letters, numbers, hyphens"
    if (not partial) or ("title" in body):
        title = str(body.get("title") or "").strip()
        if not title:
            return "title is required"
    if "image_url" in body and not valid_http_url_or_empty(body.get("image_url")):
        return "image_url must be http(s)"
    if "affiliate_url" in body and not valid_http_url_or_empty(body.get("affiliate_url")):
        return "affiliate_url must be http(s)"
    if "lang" in body and norm_lang(body.get("lang")) not in ("en", "de"):
        return "invalid lang"
    return None


def validate_post_payload(body: dict[str, Any], *, partial: bool = False) -> str | None:
    if (not partial) or ("slug" in body):
        slug = clean_slug(body.get("slug"))
        if not slug:
            return "slug is required"
        if not valid_slug(slug):
            return "invalid slug: use lowercase letters, numbers, hyphens"
    if (not partial) or ("title" in body):
        title = str(body.get("title") or "").strip()
        if not title:
            return "title is required"
    if "hero_image_url" in body and not valid_http_url_or_empty(body.get("hero_image_url")):
        return "hero_image_url must be http(s)"
    if "published_at" in body and str(body.get("published_at") or "").strip():
        try:
            datetime.fromisoformat(str(body.get("published_at")))
        except Exception:
            return "published_at must be ISO 8601"
    if "lang" in body and norm_lang(body.get("lang")) not in ("en", "de"):
        return "invalid lang"
    return None


def has_active_slug_conflict(con: sqlite3.Connection, table: str, lang: str, slug: str, *, exclude_id: int | None = None) -> bool:
    if exclude_id is None:
        row = con.execute(f"SELECT id FROM {table} WHERE lang=? AND slug=? AND active=1 LIMIT 1", (lang, slug)).fetchone()
    else:
        row = con.execute(
            f"SELECT id FROM {table} WHERE lang=? AND slug=? AND active=1 AND id<>? LIMIT 1",
            (lang, slug, exclude_id),
        ).fetchone()
    return row is not None


class Handler(SimpleHTTPRequestHandler):
    # Make SimpleHTTPRequestHandler serve from repo root
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        path = posixpath.normpath(path)
        words = [w for w in path.split("/") if w]
        p = ROOT
        for w in words:
            if w in ("..", "."):
                continue
            p = p / w
        return str(p)

    def do_OPTIONS(self):
        # same-origin dev; still respond ok
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def end_headers(self):
        # Avoid stale CSS/HTML while iterating quickly on design.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.handle_api()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.handle_api()
        return bad(self, "not found", status=404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self.handle_api()
        return bad(self, "not found", status=404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self.handle_api()
        return bad(self, "not found", status=404)

    def log_message(self, format: str, *args) -> None:
        # quieter logs
        print("[vitalcore]", format % args)

    def handle_api(self):
        ensure_db()

        # CORS for local tooling is handled in send_json/do_OPTIONS.

        # Parse path
        path = self.path.split("?", 1)[0]
        q = ""
        if "?" in self.path:
            q = self.path.split("?", 1)[1]

        qs = parse_qs(q, keep_blank_values=True) if q else {}

        def query_param(name: str, default: str = "") -> str:
            vals = qs.get(name)
            if not vals:
                return default
            return str(vals[0])

        lang = norm_lang(query_param("lang", "en"))

        m_prod = re.fullmatch(r"/api/products(?:/(\d+))?/?", path)
        m_post = re.fullmatch(r"/api/posts(?:/(\d+))?/?", path)

        try:
            with sqlite3.connect(DB_PATH) as con:
                con.row_factory = sqlite3.Row

                if m_prod:
                    pid = m_prod.group(1)
                    if self.command == "GET":
                        cur = con.execute(
                            """SELECT id, slug, lang, title, tag, description, bullets_json, price_old, price_new, price_unit,
                                      image_url, affiliate_url, featured, active, created_at, updated_at
                               FROM products
                               WHERE lang=? AND active=1
                               ORDER BY featured DESC, id DESC""",
                            (lang,),
                        )
                        items = [dict(r) for r in cur.fetchall()]
                        return send_json(self, {"ok": True, "items": items})

                    if self.command == "POST":
                        body = read_json(self)
                        err = validate_product_payload(body, partial=False)
                        if err:
                            return bad(self, err, status=400)
                        now = utcnow_iso()
                        bullets = body.get("bullets")
                        if not isinstance(bullets, list):
                            bullets = []
                        lang_value = norm_lang(body.get("lang"))
                        slug_value = clean_slug(body.get("slug"))
                        if has_active_slug_conflict(con, "products", lang_value, slug_value):
                            return bad(self, f"active product with slug '{slug_value}' already exists for lang '{lang_value}'", status=409)
                        con.execute(
                            """INSERT INTO products
                               (slug, lang, title, tag, description, bullets_json, price_old, price_new, price_unit,
                                image_url, affiliate_url, featured, active, created_at, updated_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                slug_value,
                                lang_value,
                                str(body.get("title") or "").strip(),
                                str(body.get("tag") or "").strip(),
                                str(body.get("description") or "").strip(),
                                json.dumps([str(x) for x in bullets]),
                                str(body.get("price_old") or "").strip(),
                                str(body.get("price_new") or "").strip(),
                                str(body.get("price_unit") or "").strip(),
                                str(body.get("image_url") or "").strip(),
                                str(body.get("affiliate_url") or "").strip(),
                                1 if body.get("featured") else 0,
                                0 if body.get("active") is False else 1,
                                now,
                                now,
                            ),
                        )
                        new_id = con.execute("SELECT last_insert_rowid() AS id").fetchone()[0]
                        con.commit()
                        return send_json(self, {"ok": True, "id": new_id})

                    if pid and self.command in ("PUT", "DELETE"):
                        now = utcnow_iso()
                        if self.command == "DELETE":
                            cur = con.execute("UPDATE products SET active=0, updated_at=? WHERE id=?", (now, int(pid)))
                            con.commit()
                            if cur.rowcount == 0:
                                return bad(self, "product not found", status=404)
                            return send_json(self, {"ok": True})

                        body = read_json(self)
                        err = validate_product_payload(body, partial=True)
                        if err:
                            return bad(self, err, status=400)
                        exists = con.execute("SELECT id FROM products WHERE id=?", (int(pid),)).fetchone()
                        if not exists:
                            return bad(self, "product not found", status=404)
                        # minimal: overwrite provided fields
                        fields = {
                            "slug": body.get("slug"),
                            "lang": (body.get("lang") or None),
                            "title": body.get("title"),
                            "tag": body.get("tag"),
                            "description": body.get("description"),
                            "bullets_json": json.dumps(body.get("bullets")) if isinstance(body.get("bullets"), list) else None,
                            "price_old": body.get("price_old"),
                            "price_new": body.get("price_new"),
                            "price_unit": body.get("price_unit"),
                            "image_url": body.get("image_url"),
                            "affiliate_url": body.get("affiliate_url"),
                            "featured": (1 if body.get("featured") else 0) if "featured" in body else None,
                            "active": (1 if body.get("active") else 0) if "active" in body else None,
                        }
                        sets = []
                        vals = []
                        for k, v in fields.items():
                            if v is None:
                                continue
                            sets.append(f"{k}=?")
                            vals.append(v)
                        next_lang = norm_lang(body.get("lang")) if "lang" in body else con.execute("SELECT lang FROM products WHERE id=?", (int(pid),)).fetchone()[0]
                        next_slug = clean_slug(body.get("slug")) if "slug" in body else con.execute("SELECT slug FROM products WHERE id=?", (int(pid),)).fetchone()[0]
                        next_active = (1 if body.get("active") else 0) if "active" in body else con.execute("SELECT active FROM products WHERE id=?", (int(pid),)).fetchone()[0]
                        if next_active == 1 and has_active_slug_conflict(con, "products", next_lang, next_slug, exclude_id=int(pid)):
                            return bad(self, f"active product with slug '{next_slug}' already exists for lang '{next_lang}'", status=409)

                        sets.append("updated_at=?")
                        vals.append(now)
                        vals.append(int(pid))
                        con.execute(f"UPDATE products SET {', '.join(sets)} WHERE id=?", tuple(vals))
                        con.commit()
                        return send_json(self, {"ok": True})

                    return bad(self, "method not allowed", status=405)

                if m_post:
                    post_id = m_post.group(1)
                    if self.command == "GET":
                        cur = con.execute(
                            """SELECT id, slug, lang, title, category, excerpt, hero_image_url, content_html,
                                      published_at, active, created_at, updated_at
                               FROM posts
                               WHERE lang=? AND active=1
                               ORDER BY published_at DESC, id DESC""",
                            (lang,),
                        )
                        items = [dict(r) for r in cur.fetchall()]
                        return send_json(self, {"ok": True, "items": items})

                    if self.command == "POST":
                        body = read_json(self)
                        err = validate_post_payload(body, partial=False)
                        if err:
                            return bad(self, err, status=400)
                        now = utcnow_iso()
                        published = str(body.get("published_at") or now)
                        lang_value = norm_lang(body.get("lang"))
                        slug_value = clean_slug(body.get("slug"))
                        if has_active_slug_conflict(con, "posts", lang_value, slug_value):
                            return bad(self, f"active post with slug '{slug_value}' already exists for lang '{lang_value}'", status=409)
                        con.execute(
                            """INSERT INTO posts
                               (slug, lang, title, category, excerpt, hero_image_url, content_html, published_at,
                                active, created_at, updated_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                slug_value,
                                lang_value,
                                str(body.get("title") or "").strip(),
                                str(body.get("category") or "").strip(),
                                str(body.get("excerpt") or "").strip(),
                                str(body.get("hero_image_url") or "").strip(),
                                str(body.get("content_html") or "").strip(),
                                published,
                                0 if body.get("active") is False else 1,
                                now,
                                now,
                            ),
                        )
                        new_id = con.execute("SELECT last_insert_rowid() AS id").fetchone()[0]
                        con.commit()
                        return send_json(self, {"ok": True, "id": new_id})

                    if post_id and self.command in ("PUT", "DELETE"):
                        now = utcnow_iso()
                        if self.command == "DELETE":
                            cur = con.execute("UPDATE posts SET active=0, updated_at=? WHERE id=?", (now, int(post_id)))
                            con.commit()
                            if cur.rowcount == 0:
                                return bad(self, "post not found", status=404)
                            return send_json(self, {"ok": True})

                        body = read_json(self)
                        err = validate_post_payload(body, partial=True)
                        if err:
                            return bad(self, err, status=400)
                        exists = con.execute("SELECT id FROM posts WHERE id=?", (int(post_id),)).fetchone()
                        if not exists:
                            return bad(self, "post not found", status=404)
                        fields = {
                            "slug": body.get("slug"),
                            "lang": (body.get("lang") or None),
                            "title": body.get("title"),
                            "category": body.get("category"),
                            "excerpt": body.get("excerpt"),
                            "hero_image_url": body.get("hero_image_url"),
                            "content_html": body.get("content_html"),
                            "published_at": body.get("published_at"),
                            "active": (1 if body.get("active") else 0) if "active" in body else None,
                        }
                        sets = []
                        vals = []
                        for k, v in fields.items():
                            if v is None:
                                continue
                            sets.append(f"{k}=?")
                            vals.append(v)
                        next_lang = norm_lang(body.get("lang")) if "lang" in body else con.execute("SELECT lang FROM posts WHERE id=?", (int(post_id),)).fetchone()[0]
                        next_slug = clean_slug(body.get("slug")) if "slug" in body else con.execute("SELECT slug FROM posts WHERE id=?", (int(post_id),)).fetchone()[0]
                        next_active = (1 if body.get("active") else 0) if "active" in body else con.execute("SELECT active FROM posts WHERE id=?", (int(post_id),)).fetchone()[0]
                        if next_active == 1 and has_active_slug_conflict(con, "posts", next_lang, next_slug, exclude_id=int(post_id)):
                            return bad(self, f"active post with slug '{next_slug}' already exists for lang '{next_lang}'", status=409)

                        sets.append("updated_at=?")
                        vals.append(now)
                        vals.append(int(post_id))
                        con.execute(f"UPDATE posts SET {', '.join(sets)} WHERE id=?", tuple(vals))
                        con.commit()
                        return send_json(self, {"ok": True})

                    return bad(self, "method not allowed", status=405)

                return bad(self, "not found", status=404)
        except ValueError as e:
            return bad(self, str(e), status=400)
        except Exception as e:
            return bad(self, f"server error: {e}", status=500)


def main():
    ensure_db()
    port = int(os.environ.get("PORT", "8001"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"VitalCore dev server running: http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
