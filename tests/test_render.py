"""
Unit Tests for Phase 2 Render Engine (runtime/render.py).
Tests:
1. Jinja2 compilation of full page HTML document
2. Deterministic navigation links and active page highlighting
3. Dynamic footer link rendering
4. Safe extraction of <main> content from redundant wrapper tags
"""

import pytest
from runtime.spec import generate_default_spec
from runtime.render import render_full_page, extract_clean_main_content


def test_render_full_page_multipage():
    prompt = "Create a rustic bakery website with 3 pages: Home with seasonal specials, Menu with prices and categories, and About Us with our story and contact form."
    spec = generate_default_spec(prompt)

    assert len(spec.pages) == 3
    home_page = spec.pages[0]
    menu_page = spec.pages[1]

    raw_home_main = """
    <section class="hero" id="hero">
      <h1>Fresh Artisanal Sourdough</h1>
      <p>Baked daily in our stone hearth oven.</p>
    </section>
    """

    rendered_home = render_full_page(spec, home_page, raw_home_main)

    # 1. Doctype & Head assertions
    assert "<!DOCTYPE html>" in rendered_home
    assert "<meta name=\"viewport\"" in rendered_home
    assert f"<title>{home_page.title}</title>" in rendered_home
    assert '<link rel="stylesheet" href="base.css">' in rendered_home
    assert '<link rel="stylesheet" href="styles.css">' in rendered_home
    assert '<script src="script.js" defer></script>' in rendered_home

    # 2. Nav assertions
    assert '<nav class="navbar"' in rendered_home
    assert 'href="index.html" class="nav-link active"' in rendered_home
    assert 'href="menu.html" class="nav-link "' in rendered_home
    assert 'href="about.html" class="nav-link "' in rendered_home

    # 3. Main content assertions
    assert '<main id="main-content" class="page-main">' in rendered_home
    assert "Fresh Artisanal Sourdough" in rendered_home

    # 4. Footer assertions
    assert '<footer class="site-footer"' in rendered_home
    assert spec.brand_name in rendered_home
    assert 'href="menu.html"' in rendered_home

    # Now verify menu page has active class on menu.html
    rendered_menu = render_full_page(spec, menu_page, "<h2>Menu Items</h2>")
    assert 'href="menu.html" class="nav-link active"' in rendered_menu
    assert 'href="index.html" class="nav-link "' in rendered_menu


def test_extract_clean_main_content():
    # If LLM returns full html wrapper
    wrapped_html = """<!DOCTYPE html>
<html>
<head><title>Duplicate</title></head>
<body>
  <nav>Old Nav</nav>
  <main>
    <section class="card">Proper Content</section>
  </main>
  <footer>Old Footer</footer>
</body>
</html>"""

    clean = extract_clean_main_content(wrapped_html)
    assert clean == '<section class="card">Proper Content</section>'
    assert "<nav>" not in clean
    assert "<footer>" not in clean
    assert "<!DOCTYPE" not in clean

