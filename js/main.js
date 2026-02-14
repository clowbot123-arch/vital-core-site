// VitalCore - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {

    // Newsletter Form
    const newsletterForm = document.querySelector('.newsletter-form');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = this.querySelector('input[type="email"]').value;

            // Save to localStorage (demo)
            let subscribers = JSON.parse(localStorage.getItem('subscribers') || '[]');
            if (!subscribers.includes(email)) {
                subscribers.push(email);
                localStorage.setItem('subscribers', JSON.stringify(subscribers));
                alert('Thank you for subscribing! ✓');
                this.reset();
            } else {
                alert('Already subscribed!');
            }
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Active nav link
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(link => {
        if (link.getAttribute('href') === currentPage) {
            link.classList.add('active');
        }
    });

    // Progressive enhancement: render products from /api when available (local dev + production Worker).
    hydrateProductsFromApi().catch(() => {
        // keep static HTML fallback
    });

    // Optional: render latest posts from /api when available.
    hydrateLatestPostsFromApi().catch(() => {
        // keep static HTML fallback
    });

    console.log('✓ VitalCore loaded');
    console.log('📍 Current page:', currentPage);
});

function getLang() {
    const lang = (document.documentElement.getAttribute('lang') || '').toLowerCase();
    if (lang === 'de' || lang === 'en') return lang;
    // fallback: infer from path
    const p = window.location.pathname || '';
    if (p.startsWith('/de/')) return 'de';
    return 'en';
}

function escapeHtml(s) {
    return String(s || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

async function fetchJsonWithTimeout(url, opts = {}, timeoutMs = 1200) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...opts, signal: ctrl.signal, headers: { 'accept': 'application/json', ...(opts.headers || {}) } });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return await res.json();
    } finally {
        clearTimeout(t);
    }
}

function parseBullets(it) {
    // dev_server returns bullets_json as a string.
    if (Array.isArray(it.bullets)) return it.bullets;
    try {
        const b = JSON.parse(it.bullets_json || '[]');
        return Array.isArray(b) ? b : [];
    } catch (e) {
        return [];
    }
}

function renderProductCard(it, lang) {
    const bullets = parseBullets(it).slice(0, 6);
    const buttonText = (lang === 'de') ? 'Produkt ansehen' : 'View product';

    const article = document.createElement('article');
    article.className = 'product-card' + (it.featured ? ' featured' : '');

    const priceUnit = (it.price_unit || '').trim();
    const unitHtml = priceUnit ? `<span class="per">${escapeHtml(priceUnit)}</span>` : '';

    const bulletsHtml = bullets.map(b => `<li>${escapeHtml(b)}</li>`).join('');

    article.innerHTML = `
        <div class="product-image">
            <img src="${escapeHtml(it.image_url || '')}" alt="${escapeHtml(it.title || '')}" loading="lazy">
        </div>
        <div class="product-body">
            <div class="product-tag">${escapeHtml(it.tag || '')}</div>
            <h3>${escapeHtml(it.title || '')}</h3>
            <p class="product-desc">${escapeHtml(it.description || '')}</p>
            <ul class="product-bullets">${bulletsHtml}</ul>
            <div class="product-price">
                <span class="old">${escapeHtml(it.price_old || '')}</span>
                <span class="new">${escapeHtml(it.price_new || '')}</span>
                ${unitHtml}
            </div>
            <a class="btn btn-primary btn-wide" href="${escapeHtml(it.affiliate_url || '#')}" target="_blank" rel="nofollow sponsored noopener">${buttonText}</a>
        </div>
    `.trim();

    return article;
}

async function hydrateProductsFromApi() {
    const grid = document.querySelector('.products-section .product-grid');
    if (!grid) return;

    const lang = getLang();
    const out = await fetchJsonWithTimeout(`/api/products?lang=${encodeURIComponent(lang)}`);
    const items = (out && out.items) ? out.items : [];

    // Fallback behavior: if API is down OR no items, keep static HTML.
    if (!Array.isArray(items) || items.length === 0) return;

    const frag = document.createDocumentFragment();
    for (const it of items) {
        frag.appendChild(renderProductCard(it, lang));
    }

    grid.replaceChildren(frag);
}

function renderPostCard(it, lang) {
    const href = `/${lang}/blog/${encodeURIComponent(it.slug || '')}.html`;

    const article = document.createElement('article');
    article.className = 'post-card';
    article.innerHTML = `
        <div class="post-content">
            <span class="post-category">${escapeHtml(it.category || '')}</span>
            <h3><a href="${escapeHtml(href)}">${escapeHtml(it.title || '')}</a></h3>
            <p>${escapeHtml(it.excerpt || '')}</p>
            <div class="post-meta"><span>Guide</span><span class="read-more">${lang === 'de' ? 'Lesen →' : 'Read →'}</span></div>
        </div>
    `.trim();
    return article;
}

async function hydrateLatestPostsFromApi() {
    const wrap = document.querySelector('.latest-posts .posts-grid');
    if (!wrap) return;

    const lang = getLang();
    const out = await fetchJsonWithTimeout(`/api/posts?lang=${encodeURIComponent(lang)}`);
    const items = (out && out.items) ? out.items : [];
    if (!Array.isArray(items) || items.length === 0) return;

    // Take the latest 3
    const top = items.slice(0, 3);
    const frag = document.createDocumentFragment();
    for (const it of top) {
        frag.appendChild(renderPostCard(it, lang));
    }
    wrap.replaceChildren(frag);
}
