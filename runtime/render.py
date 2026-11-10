"""
Render Engine - Deterministic HTML Page Assembly using Jinja2 (Phase 2).
Builds complete, accessible, responsive HTML pages from SiteSpec.
Guarantees:
- Python constructs <head>, <nav>, and <footer> from spec.nav and spec.footer_links.
- LLM writes ONLY the inner <main> content.
- Nav links are strictly relative and guaranteed to point to existing pages in spec.
- Active page is highlighted with class 'active'.
- Any accidental LLM wrapper markup (<html>, <body>, redundant <nav>/<footer>) is safely extracted.
"""

import re
from typing import Optional
from jinja2 import Template
from runtime.spec import PageSpec, SiteSpec
from runtime.theme import get_google_fonts_link

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ page.title }}</title>
  {{ google_fonts_markup }}
  <link rel="stylesheet" href="base.css">
  <link rel="stylesheet" href="styles.css">
  <script src="script.js" defer></script>
</head>
<body class="page-{{ page.id }} {{ 'theme-dark' if spec.theme.dark_mode else 'theme-light' }}">

  <!-- Deterministic Header & Navigation -->
  <header class="site-header">
    <nav class="navbar" id="main-navbar" aria-label="Main Navigation">
      <div class="nav-container container">
        <a href="index.html" class="logo brand-logo">
          <span class="logo-text">{{ spec.brand_name }}</span>
        </a>

        <!-- Navigation Links -->
        <ul class="nav-links" id="nav-links">
          {% for p in pages %}
          <li class="nav-item">
            <a href="{{ p.file }}" class="nav-link {% if p.id == page.id %}active{% endif %}" {% if p.id == page.id %}aria-current="page"{% endif %}>
              {{ p.title.split('|')[-1].strip() }}
            </a>
          </li>
          {% endfor %}
        </ul>

        <!-- Nav CTA & Mobile Menu Toggle -->
        <div class="nav-actions">
          {% if spec.site_type == 'restaurant' %}
          <a href="about.html#contact" class="btn btn-primary nav-cta">Reserve a Table</a>
          {% elif spec.site_type == 'saas' %}
          <a href="index.html#contact" class="btn btn-primary nav-cta">Get Started</a>
          {% elif spec.site_type == 'store' %}
          <a href="index.html#products" class="btn btn-primary nav-cta">Shop Now</a>
          {% else %}
          <a href="#contact" class="btn btn-primary nav-cta">Contact Us</a>
          {% endif %}
          <button class="mobile-menu-btn" id="mobile-menu-btn" aria-label="Toggle navigation menu" aria-expanded="false">
            <span class="hamburger-bar"></span>
            <span class="hamburger-bar"></span>
            <span class="hamburger-bar"></span>
          </button>
        </div>
      </div>
    </nav>
  </header>

  <!-- Main Content Area -->
  <main id="main-content" class="page-main">
    {{ main_content }}
  </main>

  <!-- Deterministic Footer -->
  <footer class="site-footer" id="main-footer">
    <div class="footer-container container">
      <div class="footer-brand">
        <h3 class="footer-logo">{{ spec.brand_name }}</h3>
        {% if spec.tagline %}
        <p class="footer-tagline">{{ spec.tagline }}</p>
        {% endif %}
      </div>

      <div class="footer-nav">
        <h4>Navigation</h4>
        <ul class="footer-links">
          {% for link in spec.footer_links %}
          <li><a href="{{ link.target }}">{{ link.label }}</a></li>
          {% endfor %}
        </ul>
      </div>

      <div class="footer-info">
        <h4>About</h4>
        <p class="footer-audience">{{ spec.audience }}</p>
        <p class="footer-tone">Experience: {{ spec.tone }}</p>
      </div>
    </div>
    <div class="footer-bottom container">
      <p class="copyright">&copy; 2026 {{ spec.brand_name }}. All rights reserved.</p>
    </div>
  </footer>

</body>
</html>
"""

_compiled_template = Template(PAGE_TEMPLATE)


def extract_clean_main_content(raw_html: str) -> str:
    """
    Extracts pure main/section content if LLM inadvertently wrapped output
    in full document tags (<!DOCTYPE>, <html>, <body>, <nav>, <footer>).
    """
    clean = raw_html.strip()

    # If LLM wrote a <main> tag, extract inside or keep the main content
    main_match = re.search(r"<main[^>]*>([\s\S]*?)</main>", clean, re.IGNORECASE)
    if main_match:
        return main_match.group(1).strip()

    # If LLM wrote <body>, extract inside body
    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", clean, re.IGNORECASE)
    if body_match:
        content = body_match.group(1).strip()
        # Strip out any redundant <header>/<nav> and <footer>
        content = re.sub(r"<header[\s\S]*?</header>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"<nav[\s\S]*?</nav>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"<footer[\s\S]*?</footer>", "", content, flags=re.IGNORECASE)
        return content.strip()

    # Strip out any standalone header/nav/footer if present
    clean = re.sub(r"<!DOCTYPE[^>]*>", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</?(?:html|head|body)[^>]*>", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<header[\s\S]*?</header>", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<nav[\s\S]*?</nav>", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<footer[\s\S]*?</footer>", "", clean, flags=re.IGNORECASE)

    return clean.strip()


def render_full_page(spec: SiteSpec, page: PageSpec, raw_main_content: str) -> str:
    """
    Renders the complete, fully formed HTML document for a specific page in the SiteSpec.
    """
    clean_main = extract_clean_main_content(raw_main_content)
    fonts_markup = get_google_fonts_link(spec.theme.font_heading, spec.theme.font_body)

    return _compiled_template.render(
        spec=spec,
        page=page,
        pages=spec.pages,
        main_content=clean_main,
        google_fonts_markup=fonts_markup
    )

