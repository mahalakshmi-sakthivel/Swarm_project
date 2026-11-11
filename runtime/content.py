"""
Content Copy System for Swarm Website Builder (Phase 6).
Provides structured, brand-tailored copy generation with zero placeholder text.
Eliminates 'Lorem ipsum', 'TODO', and empty content by providing realistic
headlines, subheadings, feature blurbs, testimonials, and CTAs matching spec.tone.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from runtime.spec import SiteSpec, PageSpec


class PageSectionCopy(BaseModel):
    title: str = Field(default="", description="Section heading")
    subtitle: str = Field(default="", description="Section subheading or kicker")
    body: str = Field(default="", description="Section narrative copy")
    bullets: List[str] = Field(default_factory=list, description="List of bullet points or feature highlights")
    cta: str = Field(default="", description="Call-to-action button text")
    alt_text: str = Field(default="", description="Accessible alt text for section images")


class PageCopy(BaseModel):
    page_id: str = Field(description="Matches PageSpec.id")
    headline: str = Field(default="", description="Main hero headline")
    subheadline: str = Field(default="", description="Main hero subheadline or tagline")
    cta_primary: str = Field(default="Get Started", description="Primary CTA text")
    cta_secondary: Optional[str] = Field(default="Learn More", description="Secondary CTA text")
    sections: Dict[str, PageSectionCopy] = Field(
        default_factory=dict,
        description="Section-specific copy keyed by section ID (e.g. 'hero', 'features')"
    )


class SiteCopy(BaseModel):
    brand_name: str = Field(description="Brand or business name")
    tagline: str = Field(description="Core value proposition or tagline")
    tone: str = Field(description="Editorial tone (e.g. professional, playful, elegant)")
    pages: List[PageCopy] = Field(default_factory=list, description="Copy for each page in the site")


# Tone-specific copywriting templates and vocabularies
TONE_PRESETS: Dict[str, Dict[str, Any]] = {
    "playful": {
        "hero_prefix": "Say hello to",
        "cta_primary": "Jump Right In",
        "cta_secondary": "See the Magic",
        "features_title": "Superpowers Included",
        "features_subtitle": "Everything you need to smile and get things done.",
        "testimonial_quote": "This changed the way our entire team creates. It's fast, delightful, and genuinely fun.",
        "contact_title": "Let's Make Something Great",
        "contact_subtitle": "Drop us a line and our friendly team will get back to you in a flash."
    },
    "elegant": {
        "hero_prefix": "Introducing the craft of",
        "cta_primary": "Reserve Your Experience",
        "cta_secondary": "Explore Our Story",
        "features_title": "Signature Details",
        "features_subtitle": "Meticulously curated with uncompromised quality and refinement.",
        "testimonial_quote": "An exceptional experience from inception to delivery. Absolute perfection in every detail.",
        "contact_title": "Private Inquiries",
        "contact_subtitle": "Connect with our atelier for bespoke reservations and personal consultations."
    },
    "bold": {
        "hero_prefix": "Unleash the power of",
        "cta_primary": "Start Building Now",
        "cta_secondary": "View Live Demos",
        "features_title": "Unrivaled Performance",
        "features_subtitle": "Engineered for speed, built for scale, and designed to dominate.",
        "testimonial_quote": "We doubled our conversions within the first week. The velocity and impact are unmatched.",
        "contact_title": "Get Started Today",
        "contact_subtitle": "Ready to elevate your game? Our specialists are standing by 24/7."
    },
    "professional": {
        "hero_prefix": "Empowering excellence with",
        "cta_primary": "Get Started",
        "cta_secondary": "Learn More",
        "features_title": "Comprehensive Capabilities",
        "features_subtitle": "Enterprise-ready reliability, streamlined workflows, and certified security.",
        "testimonial_quote": "A dependable partner that consistently delivers high value and measurable ROI for our organization.",
        "contact_title": "Contact Our Team",
        "contact_subtitle": "Schedule a discovery consultation with one of our enterprise advisors."
    }
}


def _resolve_tone_preset(tone: str) -> Dict[str, Any]:
    tone_lower = (tone or "").lower()
    for key, preset in TONE_PRESETS.items():
        if key in tone_lower:
            return preset
    return TONE_PRESETS["professional"]


def generate_default_copy(spec: SiteSpec) -> SiteCopy:
    """
    Deterministically generates rich, brand-tailored, tone-matched copy for all pages in a SiteSpec.
    Guarantees that no lorem ipsum, TODOs, or empty placeholders exist.
    """
    tone_preset = _resolve_tone_preset(spec.tone)
    brand = spec.brand_name or "Modern Studio"
    tagline = spec.tagline or f"Premium solutions designed for {spec.audience or 'discerning clients'}."

    page_copies: List[PageCopy] = []

    for page in spec.pages:
        sec_copies: Dict[str, PageSectionCopy] = {}

        for sec in page.sections:
            s_id = sec.id.lower()
            if "hero" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title=f"{tone_preset['hero_prefix']} {brand}",
                    subtitle=tagline,
                    body=f"Discover next-generation craftsmanship built specifically for {spec.audience or 'modern teams'}. Fast, intuitive, and beautifully responsive.",
                    cta=tone_preset["cta_primary"],
                    alt_text=f"{brand} showcase banner with sleek modern visuals"
                )
            elif "feature" in s_id or "service" in s_id or "menu" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title=tone_preset["features_title"],
                    subtitle=tone_preset["features_subtitle"],
                    body=f"Every element is crafted with precision to deliver maximum impact and seamless reliability.",
                    bullets=[
                        "Lightning-fast responsive performance",
                        "Architected with accessibility and clean typography",
                        "Customizable layouts tailored to your brand identity"
                    ],
                    cta=tone_preset["cta_secondary"],
                    alt_text="High-resolution preview of core product features"
                )
            elif "testimonial" in s_id or "review" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title="Client Endorsements",
                    subtitle="Trusted by industry leaders and creative visionaries worldwide.",
                    body=tone_preset["testimonial_quote"],
                    bullets=["Alex Mercer, Lead Architect", "Elena Rostova, Managing Director"],
                    cta="Read All Stories",
                    alt_text="Portraits of satisfied customers and verified reviews"
                )
            elif "pricing" in s_id or "plan" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title="Transparent Pricing",
                    subtitle="Simple, flexible tiers with zero hidden fees.",
                    body="Select the plan that matches your current scale and upgrade anytime as you grow.",
                    bullets=["Starter Tier - Core Essentials", "Pro Tier - Full Feature Suite", "Enterprise - Dedicated Support"],
                    cta="Choose Plan",
                    alt_text="Comparative breakdown of subscription tiers"
                )
            elif "contact" in s_id or "reservation" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title=tone_preset["contact_title"],
                    subtitle=tone_preset["contact_subtitle"],
                    body="Send us a message and our specialists will respond within 24 business hours.",
                    cta="Send Message",
                    alt_text="Customer support team office and consultation desk"
                )
            elif "about" in s_id or "story" in s_id:
                sec_copies[sec.id] = PageSectionCopy(
                    title=f"About {brand}",
                    subtitle=f"Driven by passion, precision, and purpose since our inception.",
                    body=f"Founded to serve {spec.audience or 'passionate users'}, {brand} blends state-of-the-art engineering with elegant aesthetic design.",
                    bullets=["Award-winning design philosophy", "Sustainable, forward-thinking practices", "Dedicated client advocacy"],
                    cta="Explore Heritage",
                    alt_text=f"The team behind {brand} collaborating in our modern design studio"
                )
            else:
                sec_copies[sec.id] = PageSectionCopy(
                    title=f"{sec.purpose.capitalize()}",
                    subtitle=f"Thoughtfully engineered for {brand}.",
                    body=f"Delivering tailored experiences and reliable results for {spec.audience or 'our global community'}.",
                    cta="Learn More",
                    alt_text=f"Visual demonstration of {sec.purpose}"
                )

        # Main hero headline for page
        p_headline = f"{brand} — {page.title}" if page.id != "index" else f"{tone_preset['hero_prefix']} {brand}"
        p_subheadline = tagline if page.id == "index" else f"Explore our {page.title.lower()} and discover what makes {brand} unique."

        page_copies.append(PageCopy(
            page_id=page.id,
            headline=p_headline,
            subheadline=p_subheadline,
            cta_primary=tone_preset["cta_primary"],
            cta_secondary=tone_preset["cta_secondary"],
            sections=sec_copies
        ))

    return SiteCopy(
        brand_name=brand,
        tagline=tagline,
        tone=spec.tone or "professional",
        pages=page_copies
    )

