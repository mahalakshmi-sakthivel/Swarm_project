"""
Deterministic Theme & Component System for Stage 2 Swarm (Phase 3).
Generates :root CSS variables, Google Fonts links, and the hand-crafted
base.css component library (.container, .section, .hero, .grid, .card,
.btn, .badge, .form, .testimonial, .pricing, .gallery, .faq, .stats).
"""

import re
from typing import List, Set
from runtime.spec import ThemeSpec


ALLOWED_COMPONENT_CLASSES: List[str] = [
    # Layout & Containers
    "container",
    "section",
    "section-header",
    "section-title",
    "section-subtitle",
    "grid",
    "grid-2",
    "grid-3",
    "grid-4",
    
    # Hero
    "hero",
    "hero-content",
    "hero-title",
    "hero-tagline",
    "hero-actions",
    "hero-image",
    
    # Cards
    "card",
    "card-header",
    "card-body",
    "card-footer",
    "card-title",
    "card-text",
    "card-icon",
    "card-image",
    
    # Buttons & Badges
    "btn",
    "btn-primary",
    "btn-outline",
    "btn-accent",
    "badge",
    "badge-primary",
    "badge-accent",
    
    # Navigation & Footers
    "navbar",
    "nav-container",
    "logo",
    "nav-links",
    "nav-item",
    "nav-link",
    "nav-cta",
    "footer",
    "site-footer",
    "footer-container",
    "footer-brand",
    "footer-links",
    "footer-copy",
    
    # Forms
    "form",
    "form-group",
    "form-label",
    "form-input",
    "form-textarea",
    "form-submit",
    
    # Specific Sections & Widgets
    "testimonial",
    "testimonial-quote",
    "testimonial-author",
    "testimonial-role",
    "testimonial-avatar",
    "pricing",
    "pricing-card",
    "pricing-featured",
    "pricing-header",
    "pricing-title",
    "pricing-price",
    "pricing-features",
    "pricing-feature-item",
    "gallery",
    "gallery-grid",
    "gallery-item",
    "gallery-caption",
    "faq",
    "faq-item",
    "faq-question",
    "faq-answer",
    "stats",
    "stat-item",
    "stat-number",
    "stat-label",
]

ALLOWED_COMPONENT_CLASSES_SET: Set[str] = set(ALLOWED_COMPONENT_CLASSES)


def hex_to_rgb(hex_color: str) -> str:
    """Helper to convert #rrggbb or #rgb to 'r, g, b' for rgba() usage."""
    hex_clean = hex_color.strip().lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return "37, 99, 235"  # fallback rgb
    try:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return f"{r}, {g}, {b}"
    except ValueError:
        return "37, 99, 235"


def get_google_fonts_link(font_heading: str, font_body: str) -> str:
    """Generate <link> markup for Google Fonts if recognized web fonts are specified."""
    recognized_google_fonts = {
        "inter": "Inter:wght@400;500;600;700;800",
        "poppins": "Poppins:wght@400;500;600;700",
        "playfair display": "Playfair+Display:ital,wght@0,400;0,700;1,400",
        "merriweather": "Merriweather:wght@300;400;700",
        "outfit": "Outfit:wght@400;500;600;700",
        "space grotesk": "Space+Grotesk:wght@400;500;600;700",
        "cinzel": "Cinzel:wght@400;700",
        "syne": "Syne:wght@500;700;800",
        "plus jakarta sans": "Plus+Jakarta+Sans:wght@400;500;600;700",
        "lora": "Lora:ital,wght@0,400;0,600;1,400",
        "montserrat": "Montserrat:wght@400;500;600;700",
    }

    families_to_load = []
    for f in (font_heading, font_body):
        f_clean = f.lower().split(",")[0].strip().strip("'\"")
        if f_clean in recognized_google_fonts and recognized_google_fonts[f_clean] not in families_to_load:
            families_to_load.append(recognized_google_fonts[f_clean])

    if not families_to_load:
        return ""

    query = "&family=".join(families_to_load)
    return (
        f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="https://fonts.googleapis.com/css2?family={query}&display=swap" rel="stylesheet">'
    )


def generate_root_css(theme: ThemeSpec) -> str:
    """Generate comprehensive, accessible :root CSS custom properties from ThemeSpec."""
    primary_rgb = hex_to_rgb(theme.primary)
    accent_rgb = hex_to_rgb(theme.accent)
    bg_rgb = hex_to_rgb(theme.bg)
    border_color = f"rgba({hex_to_rgb(theme.text)}, 0.12)"

    radius = theme.radius or "8px"
    # Derive radius scale
    radius_sm = "4px"
    radius_lg = "16px"
    if "px" in radius:
        try:
            val = int(re.sub(r"[^\d]", "", radius))
            radius_sm = f"{max(2, val // 2)}px"
            radius_lg = f"{val * 2}px"
        except ValueError:
            pass

    return f""":root {{
  /* Primary Theme Colors */
  --primary: {theme.primary};
  --primary-rgb: {primary_rgb};
  --secondary: {theme.secondary};
  --accent: {theme.accent};
  --accent-rgb: {accent_rgb};
  
  /* Surface & Background */
  --bg-primary: {theme.bg};
  --bg-surface: {theme.bg_surface};
  --bg-card: {theme.bg_surface};
  --border-color: {border_color};

  /* Typography Colors */
  --text-primary: {theme.text};
  --text-secondary: {theme.text_muted};
  --text-muted: {theme.text_muted};

  /* Fonts */
  --font-heading: {theme.font_heading};
  --font-body: {theme.font_body};

  /* Radius Scale */
  --radius-sm: {radius_sm};
  --radius: {radius};
  --radius-lg: {radius_lg};
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  --shadow: {theme.shadow};
  --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.35), 0 10px 10px -5px rgba(0, 0, 0, 0.2);

  /* Spacing Scale */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2.5rem;
  --space-2xl: 4rem;
}}"""


def generate_base_css(theme: ThemeSpec) -> str:
    """
    Generate production-grade base.css component library.
    Includes :root variables, reset, typography, containers, grid, hero,
    cards, buttons, badges, forms, testimonials, pricing, gallery, faq, stats.
    """
    root_block = generate_root_css(theme)

    return f"""/* ==========================================================================
   BASE.CSS - Deterministic Hand-Crafted Component Library
   Theme Mood: {theme.mood} | Dark Mode: {theme.dark_mode}
   ========================================================================== */

{root_block}

/* 1. Reset & Global Box Sizing */
*, *::before, *::after {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

html {{
  scroll-behavior: smooth;
  font-size: 16px;
}}

body {{
  font-family: var(--font-body);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

main#main-content {{
  flex: 1 0 auto;
}}

/* 2. Accessible Focus States & Links */
a {{
  color: var(--primary);
  text-decoration: none;
  transition: color 0.15s ease, opacity 0.15s ease;
}}

a:hover {{
  color: var(--accent);
}}

a:focus-visible,
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}}

/* 3. Typography */
h1, h2, h3, h4, h5, h6 {{
  font-family: var(--font-heading);
  color: var(--text-primary);
  line-height: 1.25;
  font-weight: 700;
  margin-bottom: 0.75rem;
}}

h1 {{ font-size: clamp(2rem, 4vw, 3.25rem); }}
h2 {{ font-size: clamp(1.6rem, 3vw, 2.25rem); }}
h3 {{ font-size: clamp(1.25rem, 2.5vw, 1.75rem); }}
h4 {{ font-size: 1.25rem; }}

p {{
  margin-bottom: 1rem;
  color: var(--text-secondary);
}}

p:last-child {{
  margin-bottom: 0;
}}

img {{
  max-width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius);
}}

/* 4. Layout & Containers */
.container {{
  width: 100%;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}}

.section {{
  padding-top: var(--space-2xl);
  padding-bottom: var(--space-2xl);
  position: relative;
}}

.section-header {{
  text-align: center;
  max-width: 720px;
  margin: 0 auto var(--space-xl) auto;
}}

.section-title {{
  margin-bottom: 0.5rem;
}}

.section-subtitle {{
  font-size: 1.125rem;
  color: var(--text-secondary);
}}

/* 5. Responsive Grids */
.grid {{
  display: grid;
  gap: var(--space-lg);
}}

.grid-2 {{
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}}

.grid-3 {{
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}}

.grid-4 {{
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}}

/* 6. Hero Component */
.hero {{
  padding: var(--space-2xl) 0;
  background: radial-gradient(circle at 50% 20%, rgba(var(--primary-rgb), 0.12) 0%, transparent 70%);
  text-align: center;
}}

.hero-content {{
  max-width: 800px;
  margin: 0 auto;
}}

.hero-title {{
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 1rem;
}}

.hero-tagline {{
  font-size: 1.25rem;
  color: var(--text-secondary);
  margin-bottom: var(--space-lg);
  line-height: 1.6;
}}

.hero-actions {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}}

/* 7. Card Component */
.card {{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}

.card:hover {{
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: rgba(var(--primary-rgb), 0.35);
}}

.card-icon {{
  font-size: 2rem;
  margin-bottom: 1rem;
  color: var(--primary);
}}

.card-title {{
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
}}

.card-text {{
  color: var(--text-secondary);
  flex: 1 0 auto;
}}

.card-footer {{
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}}

/* 8. Buttons & Badges */
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: var(--font-body);
  font-size: 1rem;
  font-weight: 600;
  padding: 0.75rem 1.75rem;
  border-radius: var(--radius);
  border: 2px solid transparent;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
  line-height: 1.25;
}}

.btn-primary {{
  background-color: var(--primary);
  color: #ffffff !important;
  border-color: var(--primary);
  box-shadow: 0 4px 14px rgba(var(--primary-rgb), 0.35);
}}

.btn-primary:hover {{
  filter: brightness(1.1);
  transform: translateY(-1px);
}}

.btn-outline {{
  background-color: transparent;
  color: var(--text-primary) !important;
  border-color: var(--border-color);
}}

.btn-outline:hover {{
  border-color: var(--primary);
  color: var(--primary) !important;
  background-color: rgba(var(--primary-rgb), 0.05);
}}

.btn-accent {{
  background-color: var(--accent);
  color: #ffffff !important;
  border-color: var(--accent);
  box-shadow: 0 4px 14px rgba(var(--accent-rgb), 0.35);
}}

.btn-accent:hover {{
  filter: brightness(1.1);
}}

.badge {{
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: var(--radius-full);
  letter-spacing: 0.02em;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}}

.badge-primary {{
  background-color: rgba(var(--primary-rgb), 0.15);
  color: var(--primary);
  border: 1px solid rgba(var(--primary-rgb), 0.3);
}}

.badge-accent {{
  background-color: rgba(var(--accent-rgb), 0.15);
  color: var(--accent);
  border: 1px solid rgba(var(--accent-rgb), 0.3);
}}

/* 9. Navigation & Header */
.navbar {{
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.85rem 0;
}}

.nav-container {{
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.logo {{
  font-family: var(--font-heading);
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}}

.nav-links {{
  display: flex;
  align-items: center;
  list-style: none;
  gap: 1.5rem;
}}

.nav-link {{
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.95rem;
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}}

.nav-link:hover,
.nav-link.active {{
  color: var(--text-primary);
  background: rgba(var(--primary-rgb), 0.12);
}}

/* 10. Forms */
.form {{
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}}

.form-group {{
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  text-align: left;
}}

.form-label {{
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}}

.form-input,
.form-textarea {{
  width: 100%;
  padding: 0.75rem 1rem;
  font-family: var(--font-body);
  font-size: 1rem;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}

.form-input:focus,
.form-textarea:focus {{
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.2);
}}

.form-textarea {{
  min-height: 120px;
  resize: vertical;
}}

/* 11. Testimonials */
.testimonial {{
  text-align: left;
}}

.testimonial-quote {{
  font-size: 1.1rem;
  font-style: italic;
  color: var(--text-primary);
  margin-bottom: 1.25rem;
  line-height: 1.5;
}}

.testimonial-author {{
  font-weight: 700;
  color: var(--text-primary);
}}

.testimonial-role {{
  font-size: 0.85rem;
  color: var(--text-secondary);
}}

/* 12. Pricing Tables */
.pricing-card {{
  position: relative;
  text-align: center;
}}

.pricing-featured {{
  border-color: var(--primary);
  box-shadow: 0 0 25px rgba(var(--primary-rgb), 0.25);
}}

.pricing-price {{
  font-size: 2.75rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 1rem 0;
}}

.pricing-features {{
  list-style: none;
  margin: 1.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}}

.pricing-feature-item {{
  color: var(--text-secondary);
  font-size: 0.95rem;
}}

/* 13. Gallery */
.gallery-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}}

.gallery-item {{
  overflow: hidden;
  border-radius: var(--radius);
  position: relative;
}}

.gallery-item img {{
  width: 100%;
  height: 240px;
  object-fit: cover;
  transition: transform 0.3s ease;
}}

.gallery-item:hover img {{
  transform: scale(1.05);
}}

/* 14. FAQ Component */
.faq {{
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
}}

.faq-item {{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 1.25rem;
}}

.faq-question {{
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}}

.faq-answer {{
  color: var(--text-secondary);
}}

/* 15. Stats Component */
.stats {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
  text-align: center;
}}

.stat-item {{
  padding: 1.5rem;
}}

.stat-number {{
  font-size: 3rem;
  font-weight: 800;
  color: var(--primary);
  line-height: 1;
  margin-bottom: 0.5rem;
}}

.stat-label {{
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* 16. Footer */
.site-footer {{
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  padding: var(--space-xl) 0 var(--space-lg) 0;
  margin-top: auto;
}}

.footer-container {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  text-align: center;
}}

.footer-links {{
  display: flex;
  gap: 1.5rem;
  list-style: none;
  flex-wrap: wrap;
  justify-content: center;
}}

.footer-copy {{
  font-size: 0.85rem;
  color: var(--text-secondary);
}}

/* 17. Responsive Media Queries */
@media (max-width: 768px) {{
  .section {{
    padding-top: var(--space-xl);
    padding-bottom: var(--space-xl);
  }}

  .nav-container {{
    flex-direction: column;
    gap: 1rem;
  }}

  .nav-links {{
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.75rem;
  }}

  .hero {{
    padding: var(--space-xl) 0;
  }}

  .hero-actions {{
    flex-direction: column;
    width: 100%;
  }}

  .hero-actions .btn {{
    width: 100%;
  }}

  .grid-2, .grid-3, .grid-4 {{
    grid-template-columns: 1fr;
  }}
}}
"""
