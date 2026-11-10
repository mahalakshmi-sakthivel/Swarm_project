"""
Templates Engine for Stage 2 Swarm (Phase 4).
Loads hand-crafted starter layout templates from /templates per site_type
and provides few-shot structural examples for 4B LLM prompts.
"""

from pathlib import Path
import re
from typing import Optional
from runtime.spec import SiteSpec, PageSpec

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


FEW_SHOT_EXAMPLES = {
    "restaurant": """<!-- Few-shot Example for Restaurant <main> content -->
<section id="hero" class="section hero">
  <div class="container hero-content">
    <span class="badge badge-primary">Artisanal Bakery & Cafe</span>
    <h1 class="hero-title">Rustic Hearth Bakery</h1>
    <p class="hero-tagline">Stone-milled sourdough and delicate French pastries baked fresh every dawn.</p>
    <div class="hero-actions">
      <a href="menu.html" class="btn btn-primary">View Seasonal Menu</a>
      <a href="about.html#contact" class="btn btn-outline">Visit Our Bakery</a>
    </div>
  </div>
</section>

<section id="specials" class="section">
  <div class="container">
    <div class="section-header">
      <span class="badge badge-accent">Daily Bakes</span>
      <h2 class="section-title">Today's Hearth Specials</h2>
      <p class="section-subtitle">Baked in small batches with heirloom organic grains.</p>
    </div>
    <div class="grid grid-3">
      <div class="card">
        <div class="card-icon">🥖</div>
        <h3 class="card-title">Country Sourdough</h3>
        <p class="card-text">36-hour cold ferment with crisp caramelized crust and open airy crumb.</p>
        <div class="card-footer"><strong>$9.50</strong></div>
      </div>
      <div class="card">
        <div class="card-icon">🥐</div>
        <h3 class="card-title">Almond Butter Croissant</h3>
        <p class="card-text">Laminated Normandy butter layers filled with sweet roasted almond frangipane.</p>
        <div class="card-footer"><strong>$6.00</strong></div>
      </div>
      <div class="card">
        <div class="card-icon">☕</div>
        <h3 class="card-title">Batch Brew Coffee</h3>
        <p class="card-text">Single-origin Ethiopian washed roast with notes of bergamot and jasmine.</p>
        <div class="card-footer"><strong>$4.50</strong></div>
      </div>
    </div>
  </div>
</section>""",

    "saas": """<!-- Few-shot Example for SaaS <main> content -->
<section id="hero" class="section hero">
  <div class="container hero-content">
    <span class="badge badge-primary">Cloud Intelligence</span>
    <h1 class="hero-title">Automate Cloud Workflows in Minutes</h1>
    <p class="hero-tagline">Autonomous agent infrastructure with real-time observability and instant multi-region failover.</p>
    <div class="hero-actions">
      <a href="#pricing" class="btn btn-primary">Start Free 14-Day Trial</a>
      <a href="#features" class="btn btn-outline">Explore Architecture</a>
    </div>
  </div>
</section>

<section id="stats" class="section">
  <div class="container">
    <div class="stats">
      <div class="card stat-item">
        <div class="stat-number">99.99%</div>
        <div class="stat-label">Uptime SLA</div>
      </div>
      <div class="card stat-item">
        <div class="stat-number">&lt;15ms</div>
        <div class="stat-label">Global Latency</div>
      </div>
      <div class="card stat-item">
        <div class="stat-number">10M+</div>
        <div class="stat-label">Daily Events</div>
      </div>
    </div>
  </div>
</section>

<section id="features" class="section">
  <div class="container">
    <div class="section-header">
      <span class="badge badge-accent">Core Capabilities</span>
      <h2 class="section-title">Engineered for Reliability</h2>
    </div>
    <div class="grid grid-3">
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3 class="card-title">Edge Compute</h3>
        <p class="card-text">Run deterministic agent workflows right next to your end users.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔒</div>
        <h3 class="card-title">Encrypted Storage</h3>
        <p class="card-text">Hardware security module (HSM) key isolation with zero-knowledge replication.</p>
      </div>
      <div class="card">
        <div class="card-icon">📈</div>
        <h3 class="card-title">Instant Scaling</h3>
        <p class="card-text">Autoscale from 1 to 10,000 parallel worker tasks without cold-start delays.</p>
      </div>
    </div>
  </div>
</section>""",

    "portfolio": """<!-- Few-shot Example for Portfolio <main> content -->
<section id="hero" class="section hero">
  <div class="container hero-content">
    <span class="badge badge-primary">Full-Stack Engineer & Designer</span>
    <h1 class="hero-title">Designing High-Impact Digital Products</h1>
    <p class="hero-tagline">Specializing in distributed systems, clean typography, and accessible design systems.</p>
    <div class="hero-actions">
      <a href="#projects" class="btn btn-primary">View Featured Projects</a>
      <a href="#contact" class="btn btn-outline">Get In Touch</a>
    </div>
  </div>
</section>

<section id="projects" class="section">
  <div class="container">
    <div class="section-header">
      <span class="badge badge-accent">Selected Work</span>
      <h2 class="section-title">Featured Case Studies</h2>
    </div>
    <div class="grid grid-2">
      <div class="card">
        <span class="badge badge-primary">React & TypeScript</span>
        <h3 class="card-title">Decentralized Agent Console</h3>
        <p class="card-text">Real-time blackboard monitoring dashboard with live WebSocket state streaming and sub-frame layout updates.</p>
        <div class="card-footer"><a href="#contact" class="btn btn-outline">Read Case Study →</a></div>
      </div>
      <div class="card">
        <span class="badge badge-accent">Design System</span>
        <h3 class="card-title">Lumina Design System</h3>
        <p class="card-text">Comprehensive component library featuring 40+ accessible widgets, token pipelines, and automatic dark mode support.</p>
        <div class="card-footer"><a href="#contact" class="btn btn-outline">Read Case Study →</a></div>
      </div>
    </div>
  </div>
</section>""",

    "store": """<!-- Few-shot Example for E-Commerce / Store <main> content -->
<section id="hero" class="section hero">
  <div class="container hero-content">
    <span class="badge badge-accent">New Release</span>
    <h1 class="hero-title">Timeless Minimal Essentials</h1>
    <p class="hero-tagline">Sustainably sourced apparel and home goods built to endure a lifetime.</p>
    <div class="hero-actions">
      <a href="#products" class="btn btn-primary">Shop Collection</a>
      <a href="#about" class="btn btn-outline">Our Craft</a>
    </div>
  </div>
</section>

<section id="products" class="section">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Featured Goods</h2>
    </div>
    <div class="grid grid-3">
      <div class="card">
        <div class="card-icon">🧥</div>
        <h3 class="card-title">Merino Wool Overshirt</h3>
        <p class="card-text">100% extrafine ethical wool with horn buttons and tailored cuffs.</p>
        <div class="card-footer" style="display: flex; justify-content: space-between; align-items: center;">
          <strong>$180</strong>
          <button class="btn btn-primary" style="padding: 0.4rem 0.9rem; font-size: 0.85rem;">Add to Bag</button>
        </div>
      </div>
    </div>
  </div>
</section>""",

    "landing": """<!-- Few-shot Example for Landing Page <main> content -->
<section id="hero" class="section hero">
  <div class="container hero-content">
    <span class="badge badge-primary">Modern Solution</span>
    <h1 class="hero-title">Everything You Need to Succeed Online</h1>
    <p class="hero-tagline">Launch faster, convert better, and delight your users with our unified digital platform.</p>
    <div class="hero-actions">
      <a href="#signup" class="btn btn-primary">Get Started Now</a>
      <a href="#features" class="btn btn-outline">Learn More</a>
    </div>
  </div>
</section>

<section id="features" class="section">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Why Choose Us</h2>
    </div>
    <div class="grid grid-3">
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3 class="card-title">Blazing Fast</h3>
        <p class="card-text">Optimized from top to bottom for maximum speed and conversion.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔒</div>
        <h3 class="card-title">Fully Secure</h3>
        <p class="card-text">Bank-grade encryption and automated security monitoring 24/7.</p>
      </div>
      <div class="card">
        <div class="card-icon">🎯</div>
        <h3 class="card-title">Results Driven</h3>
        <p class="card-text">Built to boost engagement, sales, and long-term user retention.</p>
      </div>
    </div>
  </div>
</section>"""
}


def get_few_shot_example(site_type: str) -> str:
    """Returns few-shot example tailored to site_type (or falls back to landing)."""
    return FEW_SHOT_EXAMPLES.get(site_type.lower(), FEW_SHOT_EXAMPLES["landing"])


def load_starter_template(site_type: str, page_file: str) -> Optional[str]:
    """Loads a starter layout template from /templates for a given site type and page file."""
    type_dir = TEMPLATES_DIR / site_type.lower()
    if not type_dir.exists():
        type_dir = TEMPLATES_DIR / "landing"

    target_file = type_dir / page_file
    if target_file.exists():
        return target_file.read_text(encoding="utf-8")

    # Fallback to index.html within type directory
    index_file = type_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")

    return None


def fill_template_placeholders(template_raw: str, spec: SiteSpec, page: PageSpec) -> str:
    """Substitutes template variables (brand_name, tagline, titles) into the template."""
    hydrated = template_raw
    hydrated = hydrated.replace("{{ brand_name }}", spec.brand_name)
    hydrated = hydrated.replace("{{ tagline or \"Hand-crafted culinary creations prepared with fresh, locally sourced seasonal ingredients.\" }}", spec.tagline or "Hand-crafted culinary creations prepared with fresh, locally sourced seasonal ingredients.")
    hydrated = hydrated.replace("{{ tagline or \"Accelerate your digital workflow with autonomous intelligence, real-time analytics, and instant scaling.\" }}", spec.tagline or "Accelerate your digital workflow with autonomous intelligence, real-time analytics, and instant scaling.")
    hydrated = hydrated.replace("{{ tagline or \"Architecting refined digital products, interactive design systems, and high-performance web applications.\" }}", spec.tagline or "Architecting refined digital products, interactive design systems, and high-performance web applications.")
    hydrated = hydrated.replace("{{ tagline or \"Carefully curated lifestyle goods, timeless apparel, and sustainable homeware.\" }}", spec.tagline or "Carefully curated lifestyle goods, timeless apparel, and sustainable homeware.")
    hydrated = hydrated.replace("{{ tagline or \"Thoughtful perspectives on design systems, autonomous AI architectures, and modern web craft.\" }}", spec.tagline or "Thoughtful perspectives on design systems, autonomous AI architectures, and modern web craft.")
    hydrated = hydrated.replace("{{ tagline or \"Turn ideas into production-ready digital experiences in minutes with intelligent autonomous generation.\" }}", spec.tagline or "Turn ideas into production-ready digital experiences in minutes with intelligent autonomous generation.")
    hydrated = re.sub(r"\{\{\s*tagline[^}]*\}\}", spec.tagline or "", hydrated)
    hydrated = re.sub(r"\{\{\s*brand_name\s*\}\}", spec.brand_name, hydrated)
    return hydrated

