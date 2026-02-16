# VitalCore Context Snapshot (2026-02-14)

## Goals
- One domain/site with **real EN + DE pages** (SEO friendly): `/en/` and `/de/`.
- Content strategy: Pillar guides + recipes across 3 topics: **muscle/strength**, **fat loss**, **sleep-energy**.
- Affiliate products are top priority and must be prominent:
  - MenoPower (women 40+)
  - Advanced Amino Acid Complex (recovery/muscle preservation)
  - EndoPeak (men 40+ vitality)
- Free, copyright-free stock photos: use **Pexels**.
- Deliverables must be **Drag & Drop** ready for Cloudflare Pages.
- Local IP hosting for testing.

## Current state
- Repo: https://github.com/clowbot123-arch/vital-core-site
- Local host: `python -m http.server` on port **8001**
  - EN: http://192.168.178.98:8001/en/
  - DE: http://192.168.178.98:8001/de/
- `/` redirects to `/en/`.
- `robots.txt` + `sitemap.xml` generated.

## Fixed issues (today)
- CSS path bugs in EN articles (relative paths) → standardized to `/css/style.css`.
- DE blog was broken (wrong EN file + links like `/de/blog/blog/...` and missing pages) → created DE blog index + DE blog pages:
  - `/de/blog/index.html`
  - `/de/blog/sleep-optimization.html`
  - `/de/blog/energy-boosting-foods.html`
  - `/de/blog/muscle-building-over-40.html`
  - `/de/blog/building-muscle-after-40.html`
- Missing recipe pages that were linked but absent → created EN+DE pages:
  - `/en/recipes/overnight-oats.html` (+ greek-yogurt-parfait, grilled-salmon, mediterranean-chicken, energy-balls, hummus-veggies)
  - mirrored under `/de/recipes/`.

## Affiliate prominence
- EN homepage updated to make products highly prominent (Hero CTA → products; dedicated product cards section).
- DE homepage mirrored to EN layout with translated text.

## Next improvements
- Build automation scripts (generator + link checker + auto-zip).
- Make DE recipes/blog index pages also 1:1 premium style (remove emojis, unify cards).
- Add `ASSETS_SOURCES.md` to track Pexels source links for each image.
