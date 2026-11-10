"""
SiteSpec - Structured Architecture & Design Specification Contract (Phase 1).
Defines the Pydantic v2 data models for the shared contract between all swarm agents.
Eliminates free-form prompt ambiguity:
- Deterministic page list, section hierarchy, component classes
- Cohesive color tokens and theme specifications
- Flat checklist of concrete user requirements (R1, R2, ...)
- Explicit tracking of fallback assumptions
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class SectionSpec(BaseModel):
    id: str = Field(description="Unique HTML section anchor id, e.g. 'hero', 'menu-list', 'contact'")
    purpose: str = Field(description="Functional purpose of this section, e.g. 'Headline & call to action'")
    component: str = Field(description="Primary component pattern, e.g. 'hero', 'card-grid', 'form', 'stats'")


class PageSpec(BaseModel):
    id: str = Field(description="Unique page identifier, e.g. 'home', 'menu', 'about', 'contact'")
    file: str = Field(description="HTML filename, e.g. 'index.html', 'menu.html', 'about.html'")
    title: str = Field(description="Page title tag and heading, e.g. 'Home - Rustic Oven Bakery'")
    sections: List[SectionSpec] = Field(default_factory=list, description="Ordered sections within this page")


class ThemeSpec(BaseModel):
    mood: str = Field(default="modern", description="Overall aesthetic mood, e.g. 'rustic', 'cyberpunk', 'clean', 'pastel'")
    primary: str = Field(default="#2563eb", description="Primary brand color hex")
    secondary: str = Field(default="#475569", description="Secondary supporting color hex")
    accent: str = Field(default="#06b6d4", description="Vibrant highlight accent color hex")
    bg: str = Field(default="#0f172a", description="Main page background color hex")
    bg_surface: str = Field(default="#1e293b", description="Card / elevated surface background hex")
    text: str = Field(default="#f8fafc", description="Primary body and heading text color hex")
    text_muted: str = Field(default="#94a3b8", description="Secondary / muted text color hex")
    font_heading: str = Field(default="system-ui, -apple-system, sans-serif", description="Font family for headings")
    font_body: str = Field(default="system-ui, -apple-system, sans-serif", description="Font family for body copy")
    radius: str = Field(default="8px", description="Default border-radius (e.g. '8px', '12px', '9999px')")
    shadow: str = Field(default="0 10px 25px -5px rgba(0, 0, 0, 0.3)", description="Default elevation box-shadow")
    dark_mode: bool = Field(default=True, description="Whether the theme is dark mode")


class FooterLink(BaseModel):
    label: str
    target: str


class RequirementItem(BaseModel):
    id: str = Field(description="Requirement identifier, e.g. 'R1', 'R2', 'R3'")
    description: str = Field(description="Concrete user requirement description")
    category: str = Field(default="general", description="Category: 'layout', 'theme', 'feature', 'content'")


class SiteSpec(BaseModel):
    site_type: Literal["portfolio", "restaurant", "saas", "store", "blog", "landing", "other"] = "landing"
    brand_name: str = Field(default="Brand", description="Company or project brand name")
    tagline: str = Field(default="", description="Catchy one-line slogan or value proposition")
    audience: str = Field(default="General audience", description="Target customer or audience")
    tone: str = Field(default="professional and modern", description="Voice tone, e.g. 'warm & artisanal', 'sleek & tech-forward'")
    pages: List[PageSpec] = Field(default_factory=list, description="All pages in the website")
    nav: List[str] = Field(default_factory=list, description="Ordered list of page IDs for header navigation")
    footer_links: List[FooterLink] = Field(default_factory=list, description="Footer navigation items")
    theme: ThemeSpec = Field(default_factory=ThemeSpec, description="Deterministic visual theme tokens")
    features: List[str] = Field(default_factory=list, description="Interactive feature tags, e.g. 'mobile-menu', 'contact-form-validation'")
    requirements: List[RequirementItem] = Field(default_factory=list, description="Checklist of concrete prompt requirements")
    assumptions: List[str] = Field(default_factory=list, description="Sensible defaults filled when prompt was ambiguous")


def detect_site_type(prompt: str) -> Literal["portfolio", "restaurant", "saas", "store", "blog", "landing", "other"]:
    p = prompt.lower()
    if any(k in p for k in ["portfolio", "resume", "cv", "personal site", "developer portfolio"]):
        return "portfolio"
    if any(k in p for k in ["restaurant", "bakery", "cafe", "coffee", "bistro", "food", "menu", "pizza", "dining"]):
        return "restaurant"
    if any(k in p for k in ["saas", "software", "app", "startup", "platform", "dashboard", "api", "cloud"]):
        return "saas"
    if any(k in p for k in ["store", "shop", "ecommerce", "e-commerce", "boutique", "product"]):
        return "store"
    if any(k in p for k in ["blog", "news", "journal", "magazine", "articles"]):
        return "blog"
    if any(k in p for k in ["landing", "agency", "studio", "business"]):
        return "landing"
    return "other"


def generate_default_spec(prompt: str) -> SiteSpec:
    """
    Deterministic synthesizer: Generates a complete, high-quality SiteSpec from any user prompt.
    Used when the prompt is brief or when an LLM planning call needs sensible defaults.
    """
    site_type = detect_site_type(prompt)
    p_lower = prompt.lower()
    assumptions = []

    # Detect dark/light preference
    is_dark = True
    if "light mode" in p_lower or "light theme" in p_lower or "white background" in p_lower:
        is_dark = False
    elif "dark mode" in p_lower or "dark theme" in p_lower or "black background" in p_lower:
        is_dark = True
    else:
        # Default to dark mode for tech/saas/portfolio, warm light for bakery/restaurant
        if site_type == "restaurant":
            is_dark = False
            assumptions.append("Chose warm light palette suitable for culinary/hospitality domain")
        else:
            is_dark = True
            assumptions.append("Chose modern dark mode aesthetic")

    # Generate Theme
    if site_type == "restaurant":
        theme = ThemeSpec(
            mood="rustic & warm",
            primary="#b45309" if is_dark else "#d97706",
            secondary="#78350f" if is_dark else "#451a03",
            accent="#f59e0b",
            bg="#1c1917" if is_dark else "#fdfbf7",
            bg_surface="#292524" if is_dark else "#ffffff",
            text="#fafaf9" if is_dark else "#292524",
            text_muted="#a8a29e" if is_dark else "#78716c",
            radius="10px",
            dark_mode=is_dark
        )
        brand = "Artisanal Kitchen"
        tagline = "Freshly Crafted with Heritage & Passion"
    elif site_type == "saas":
        theme = ThemeSpec(
            mood="high-tech modern",
            primary="#6366f1",
            secondary="#4f46e5",
            accent="#06b6d4",
            bg="#0b0f19" if is_dark else "#f8fafc",
            bg_surface="#1e2335" if is_dark else "#ffffff",
            text="#ffffff" if is_dark else "#0f172a",
            text_muted="#94a3b8" if is_dark else "#64748b",
            radius="8px",
            dark_mode=is_dark
        )
        brand = "NexusAI"
        tagline = "Intelligent Workflows for High-Velocity Teams"
    elif site_type == "portfolio":
        theme = ThemeSpec(
            mood="creative & minimal",
            primary="#8b5cf6",
            secondary="#6d28d9",
            accent="#ec4899",
            bg="#090d16" if is_dark else "#f8fafc",
            bg_surface="#161f30" if is_dark else "#ffffff",
            text="#ffffff" if is_dark else "#111827",
            text_muted="#94a3b8" if is_dark else "#4b5563",
            radius="12px",
            dark_mode=is_dark
        )
        brand = "Alex Morgan"
        tagline = "Full-Stack Engineer & AI Systems Architect"
    else:
        theme = ThemeSpec(
            mood="sleek & polished",
            primary="#3b82f6",
            secondary="#1d4ed8",
            accent="#10b981",
            bg="#0f172a" if is_dark else "#ffffff",
            bg_surface="#1e293b" if is_dark else "#f1f5f9",
            text="#f8fafc" if is_dark else "#0f172a",
            text_muted="#94a3b8" if is_dark else "#64748b",
            radius="8px",
            dark_mode=is_dark
        )
        brand = "Lumina Studio"
        tagline = "Elevating Digital Experiences"

    # Multi-page detection: check if user asked for multiple pages
    pages = []
    if any(k in p_lower for k in ["3 page", "3-page", "multi-page", "multiple pages", "about page", "menu page", "contact page"]):
        if site_type == "restaurant":
            pages = [
                PageSpec(
                    id="home",
                    file="index.html",
                    title=f"{brand} | Home",
                    sections=[
                        SectionSpec(id="hero", purpose="Brand welcome and signature specials", component="hero"),
                        SectionSpec(id="specials", purpose="Curated daily artisanal highlights", component="card-grid"),
                        SectionSpec(id="testimonials", purpose="Guest quotes and culinary awards", component="testimonial"),
                    ]
                ),
                PageSpec(
                    id="menu",
                    file="menu.html",
                    title=f"{brand} | Seasonal Menu",
                    sections=[
                        SectionSpec(id="menu-header", purpose="Menu introduction & dietary guide", component="hero"),
                        SectionSpec(id="menu-categories", purpose="Categorized dishes with pricing", component="card-grid"),
                    ]
                ),
                PageSpec(
                    id="about",
                    file="about.html",
                    title=f"{brand} | Our Story & Reservations",
                    sections=[
                        SectionSpec(id="story", purpose="Origins and local ingredients ethos", component="section"),
                        SectionSpec(id="contact", purpose="Table reservation & inquiry form", component="form"),
                    ]
                )
            ]
        elif site_type == "saas":
            pages = [
                PageSpec(
                    id="home",
                    file="index.html",
                    title=f"{brand} | Intelligent Platform",
                    sections=[
                        SectionSpec(id="hero", purpose="Core value proposition and CTA", component="hero"),
                        SectionSpec(id="features", purpose="Feature breakdown and capabilities", component="card-grid"),
                        SectionSpec(id="stats", purpose="Key scale metrics and performance KPIs", component="stats"),
                    ]
                ),
                PageSpec(
                    id="pricing",
                    file="pricing.html",
                    title=f"{brand} | Pricing Plans",
                    sections=[
                        SectionSpec(id="pricing-tiers", purpose="Tiered subscription pricing plans", component="pricing"),
                        SectionSpec(id="faq", purpose="Frequently asked questions", component="faq"),
                    ]
                ),
                PageSpec(
                    id="contact",
                    file="contact.html",
                    title=f"{brand} | Contact & Enterprise Sales",
                    sections=[
                        SectionSpec(id="contact-form", purpose="Inquiry and sales demo form", component="form"),
                    ]
                )
            ]
        else:
            pages = [
                PageSpec(
                    id="home",
                    file="index.html",
                    title=f"{brand} | Home",
                    sections=[
                        SectionSpec(id="hero", purpose="Introduction and featured work", component="hero"),
                        SectionSpec(id="showcase", purpose="Primary portfolio projects", component="card-grid"),
                    ]
                ),
                PageSpec(
                    id="about",
                    file="about.html",
                    title=f"{brand} | About & Background",
                    sections=[
                        SectionSpec(id="bio", purpose="Background, skills, and experience", component="section"),
                        SectionSpec(id="contact", purpose="Contact details and inquiry form", component="form"),
                    ]
                )
            ]
        assumptions.append(f"Structured multi-page site with {len(pages)} distinct pages")
    else:
        # Single page with modular anchor sections
        pages = [
            PageSpec(
                id="home",
                file="index.html",
                title=f"{brand} | {tagline}",
                sections=[
                    SectionSpec(id="hero", purpose="Headline and primary call to action", component="hero"),
                    SectionSpec(id="features", purpose="Core offerings or showcases", component="card-grid"),
                    SectionSpec(id="contact", purpose="User inquiry or order form", component="form"),
                ]
            )
        ]
        assumptions.append("Synthesized unified single-page layout with anchor navigation")

    # Navigation & Footer
    nav = [p.id for p in pages]
    footer_links = [FooterLink(label=p.title.split("|")[-1].strip(), target=p.file) for p in pages]

    # Concrete Requirements Checklist
    requirements = [
        RequirementItem(id="R1", description=f"Site category conforms to '{site_type}' domain layout", category="layout"),
        RequirementItem(id="R2", description=f"Theme adheres to {theme.mood} ({'dark' if theme.dark_mode else 'light'} mode)", category="theme"),
        RequirementItem(id="R3", description=f"Generate {len(pages)} valid page file(s): {', '.join(p.file for p in pages)}", category="layout"),
        RequirementItem(id="R4", description="Deterministic navigation linking all generated pages without 404s", category="feature"),
        RequirementItem(id="R5", description="Responsive design on mobile (390px) and desktop (1280px)", category="feature"),
    ]

    features = ["mobile-menu", "smooth-scroll", "contact-form-validation"]

    return SiteSpec(
        site_type=site_type,
        brand_name=brand,
        tagline=tagline,
        audience="Customers and visitors seeking " + brand,
        tone=theme.mood,
        pages=pages,
        nav=nav,
        footer_links=footer_links,
        theme=theme,
        features=features,
        requirements=requirements,
        assumptions=assumptions
    )


def parse_or_repair_spec(raw: Any, prompt: str) -> SiteSpec:
    """
    Validates candidate raw JSON/dict into a SiteSpec, gracefully repairing
    missing fields using prompt-aware deterministic defaults.
    """
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return generate_default_spec(prompt)

    if not isinstance(raw, dict):
        return generate_default_spec(prompt)

    try:
        # Direct validation
        spec = SiteSpec(**raw)
        if len(spec.pages) == 0:
            default_spec = generate_default_spec(prompt)
            spec.pages = default_spec.pages
            spec.nav = default_spec.nav
            spec.footer_links = default_spec.footer_links
            spec.assumptions.append("Added default page hierarchy matching site type")
        return spec
    except Exception:
        # Partial recovery: merge candidate data over default template
        base_spec = generate_default_spec(prompt)
        base_dict = base_spec.model_dump()

        # Update base with any valid top-level fields from raw
        for k in ["site_type", "brand_name", "tagline", "audience", "tone", "features"]:
            if k in raw and raw[k]:
                base_dict[k] = raw[k]

        if "theme" in raw and isinstance(raw["theme"], dict):
            base_dict["theme"].update({k: v for k, v in raw["theme"].items() if v is not None})

        if "pages" in raw and isinstance(raw["pages"], list) and len(raw["pages"]) > 0:
            try:
                parsed_pages = [PageSpec(**p) if isinstance(p, dict) else p for p in raw["pages"]]
                base_dict["pages"] = [p.model_dump() for p in parsed_pages]
                base_dict["nav"] = [p.id for p in parsed_pages]
            except Exception:
                pass

        if "requirements" in raw and isinstance(raw["requirements"], list) and len(raw["requirements"]) > 0:
            try:
                base_dict["requirements"] = raw["requirements"]
            except Exception:
                pass

        return SiteSpec(**base_dict)
